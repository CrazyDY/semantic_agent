export type SemanticEventType =
  | 'run.start'
  | 'run.end'
  | 'step.start'
  | 'step.end'
  | 'thinking.start'
  | 'thinking.delta'
  | 'thinking.end'
  | 'message.start'
  | 'message.delta'
  | 'message.end'
  | 'tool_call.start'
  | 'tool_call.delta'
  | 'tool_call.end'
  | 'tool_execute.start'
  | 'tool_execute.end'
  | 'error'

export interface SemanticEvent<T = Record<string, unknown>> {
  type: SemanticEventType | string
  data: T
}
