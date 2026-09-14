export interface ToolCallState {
  callId: string
  name: string
  index: number
  arguments: string
  parsedArguments: unknown | null
  status: 'calling' | 'running' | 'success' | 'error'
  result: unknown | null
  error: string | null
}

export interface AssistantTurn {
  id: string
  runId: string | null
  stepId: string | null
  thinking: string
  thinkingDone: boolean
  thinkingExpanded: boolean
  content: string
  streaming: boolean
  tools: ToolCallState[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content?: string
  attachments?: ImageAttachment[]
  turn?: AssistantTurn
}

export interface ImageAttachment {
  id: string
  name: string
  url: string
}
