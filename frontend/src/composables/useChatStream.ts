import { nextTick, ref } from 'vue'
import type { ChatMessage, ToolCallState } from '../types/chat'
import type { SemanticEvent } from '../types/events'

interface EventHandlers {
  onEvent?: (event: SemanticEvent) => void
}

const API_URL = import.meta.env.VITE_API_URL || '/chat'

export function useChatStream(handlers: EventHandlers = {}) {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const error = ref<string | null>(null)

  let activeAssistant: ChatMessage | null = null

  function ensureAssistant(data: Record<string, unknown>): AssistantTurnTarget {
    if (!activeAssistant || activeAssistant.role !== 'assistant' || !activeAssistant.turn) {
      const id = String(data.message_id || `assistant_${Date.now()}`)
      const turn = {
        id,
        runId: data.run_id ? String(data.run_id) : null,
        stepId: data.step_id ? String(data.step_id) : null,
        thinking: '',
        thinkingDone: false,
        thinkingExpanded: true,
        content: '',
        streaming: true,
        tools: [],
      }
      // Important: messages.value is a Vue reactive array. After push(), Vue
      // wraps the inserted object in a Proxy. Keep that reactive Proxy as the
      // active reference; mutating the original raw object would bypass Vue's
      // reactivity and streaming chunks would not render incrementally.
      messages.value.push({ id, role: 'assistant', turn })
      activeAssistant = messages.value[messages.value.length - 1]
    }
    return { message: activeAssistant, turn: activeAssistant.turn! }
  }

  function findTool(turn: NonNullable<ChatMessage['turn']>, callId?: string, index?: number) {
    return turn.tools.find((tool) => (callId && tool.callId === callId) || tool.index === index)
  }

  function handle(event: SemanticEvent) {
    handlers.onEvent?.(event)
    const data = event.data as Record<string, unknown>

    switch (event.type) {
      case 'run.start':
        break

      case 'step.start': {
        const { turn } = ensureAssistant(data)
        turn.stepId = data.step_id ? String(data.step_id) : turn.stepId
        turn.runId = data.run_id ? String(data.run_id) : turn.runId
        break
      }

      case 'thinking.start': {
        const { turn } = ensureAssistant(data)
        turn.thinkingDone = false
        turn.thinkingExpanded = true
        break
      }

      case 'thinking.delta': {
        const { turn } = ensureAssistant(data)
        turn.thinking += String(data.delta ?? '')
        break
      }

      case 'thinking.end': {
        const { turn } = ensureAssistant(data)
        turn.thinkingDone = true
        turn.thinkingExpanded = false
        break
      }

      case 'message.start':
        ensureAssistant(data)
        break

      case 'message.delta': {
        const { turn } = ensureAssistant(data)
        turn.content += String(data.delta ?? '')
        turn.streaming = true
        break
      }

      case 'message.end': {
        const { turn } = ensureAssistant(data)
        turn.streaming = false
        break
      }

      case 'tool_call.start': {
        const { turn } = ensureAssistant(data)
        const tool: ToolCallState = {
          callId: String(data.call_id ?? `tool_${turn.tools.length}`),
          name: String(data.name ?? 'tool'),
          index: Number(data.index ?? turn.tools.length),
          arguments: '',
          parsedArguments: null,
          status: 'calling',
          result: null,
          error: null,
        }
        turn.tools.push(tool)
        break
      }

      case 'tool_call.delta': {
        const { turn } = ensureAssistant(data)
        const tool = findTool(turn, data.call_id ? String(data.call_id) : undefined, Number(data.index))
        if (tool) tool.arguments += String(data.delta ?? '')
        break
      }

      case 'tool_call.end': {
        const { turn } = ensureAssistant(data)
        const tool = findTool(turn, data.call_id ? String(data.call_id) : undefined, Number(data.index))
        if (tool) {
          tool.parsedArguments = data.arguments ?? null
          tool.arguments = String(data.arguments_raw ?? tool.arguments)
          tool.status = 'calling'
        }
        break
      }

      case 'tool_execute.start': {
        const { turn } = ensureAssistant(data)
        const tool = findTool(turn, data.call_id ? String(data.call_id) : undefined)
        if (tool) tool.status = 'running'
        break
      }

      case 'tool_execute.end': {
        const { turn } = ensureAssistant(data)
        const tool = findTool(turn, data.call_id ? String(data.call_id) : undefined)
        if (tool) {
          tool.result = data.result ?? null
          tool.error = data.error ? String(data.error) : null
          tool.status = tool.error ? 'error' : 'success'
        }
        break
      }

      case 'step.end':
        break

      case 'run.end': {
        if (activeAssistant?.turn) activeAssistant.turn.streaming = false
        break
      }

      case 'error':
        error.value = String(data.message ?? '请求失败')
        if (activeAssistant?.turn) activeAssistant.turn.streaming = false
        break
    }
  }

  async function sendMessage(text: string) {
    const content = text.trim()
    if (!content || isStreaming.value) return false

    error.value = null
    isStreaming.value = true
    activeAssistant = null

    messages.value.push({
      id: `user_${Date.now()}`,
      role: 'user',
      content,
    })

    await nextTick()

    const payload = {
      messages: messages.value.map((message) => {
        if (message.role === 'user') return { role: 'user', content: message.content ?? '' }
        const tools = message.turn?.tools ?? []
        const content = message.turn?.content ?? ''
        if (tools.length) {
          return {
            role: 'assistant',
            content: content || null,
            tool_calls: tools.map((tool) => ({
              id: tool.callId,
              type: 'function',
              function: { name: tool.name, arguments: tool.arguments },
            })),
          }
        }
        return { role: 'assistant', content }
      }),
    }

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(payload),
      })

      if (!response.ok || !response.body) {
        throw new Error(await response.text())
      }

      await consumeSSE(response.body)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '请求失败'
      if (!activeAssistant) {
        messages.value.push({ id: `error_${Date.now()}`, role: 'assistant', content: error.value })
      }
      return false
    } finally {
      isStreaming.value = false
      if (activeAssistant?.turn) activeAssistant.turn.streaming = false
    }
  }

  async function consumeSSE(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const blocks = buffer.split(/\r?\n\r?\n/)
        buffer = blocks.pop() ?? ''
        for (const block of blocks) parseEventBlock(block)
      }
      buffer += decoder.decode()
      if (buffer.trim()) parseEventBlock(buffer)
    } finally {
      reader.releaseLock()
    }
  }

  function parseEventBlock(block: string) {
    let type = ''
    let data = ''
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) type = line.slice(6).trim()
      else if (line.startsWith('data:')) data += line.slice(5).trim()
    }
    if (!type || !data) return
    try {
      handle({ type, data: JSON.parse(data) })
    } catch {
      // Ignore malformed SSE event blocks so a single bad chunk does not crash the UI.
    }
  }

  function reset() {
    messages.value = []
    activeAssistant = null
    error.value = null
  }

  return { messages, isStreaming, error, sendMessage, reset }
}

type AssistantTurnTarget = { message: ChatMessage; turn: NonNullable<ChatMessage['turn']> }
