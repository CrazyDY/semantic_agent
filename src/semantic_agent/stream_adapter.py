from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .events import AgentEvent


@dataclass(slots=True)
class ToolCallState:
    index: int
    call_id: str | None = None
    name: str | None = None
    arguments: str = ""
    started: bool = False
    ended: bool = False


class ChatCompletionStreamAdapter:
    """Convert one Chat Completions stream into semantic events.

    The adapter is intentionally provider-tolerant. In addition to the standard
    delta.content/tool_calls fields, it accepts common reasoning_content/reasoning
    extensions used by OpenAI-compatible endpoints.
    """

    def __init__(self, run_id: str | None = None, step_id: str | None = None):
        self.run_id = run_id
        self.step_id = step_id
        self.reasoning_started = False
        self.reasoning_id = f"{run_id or 'run'}_reasoning"
        self.message_started = False
        self.message_id = f"{run_id or 'run'}_message"
        self.tool_calls: dict[int, ToolCallState] = {}
        self.finish_reason: str | None = None

    def process(self, chunk: dict[str, Any]) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        choices = chunk.get("choices") or []
        if not choices:
            return events

        for choice in choices:
            delta = choice.get("delta") or {}

            reasoning = self._reasoning_delta(delta)
            if reasoning:
                if not self.reasoning_started:
                    self.reasoning_started = True
                    events.append(self._event("thinking.start", {"id": self.reasoning_id}))
                events.append(self._event("thinking.delta", {"id": self.reasoning_id, "delta": reasoning}))

            content = delta.get("content")
            if isinstance(content, str) and content:
                # A new visible content phase closes reasoning first so the
                # semantic event stream reflects a real lifecycle boundary.
                events.extend(self._end_thinking())
                if not self.message_started:
                    self.message_started = True
                    events.append(self._event("message.start", {"id": self.message_id}))
                events.append(self._event("message.delta", {"id": self.message_id, "delta": content}))

            tool_deltas = delta.get("tool_calls") or []
            if tool_deltas:
                # Tool calling is another phase. Close any preceding reasoning
                # and visible-message phase before starting the tool phase.
                events.extend(self._end_thinking())
                events.extend(self._end_message())
                for tool_delta in tool_deltas:
                    events.extend(self._process_tool_call(tool_delta))

            finish_reason = choice.get("finish_reason")
            if finish_reason:
                self.finish_reason = finish_reason
                events.extend(self.finalize())

        return events

    def finalize(self) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        events.extend(self._end_thinking())

        # Tool calls are completed by finish_reason=tool_calls. Close them
        # before any remaining message lifecycle is finalized.
        for state in self.tool_calls.values():
            if state.started and not state.ended:
                arguments = self._parse_arguments(state.arguments)
                events.append(self._event("tool_call.end", {
                    "call_id": state.call_id,
                    "name": state.name,
                    "index": state.index,
                    "arguments": arguments,
                    "arguments_raw": state.arguments,
                }))
                state.ended = True

        events.extend(self._end_message())
        return events

    def _end_message(self) -> list[AgentEvent]:
        if not self.message_started:
            return []

        self.message_started = False
        return [self._event("message.end", {"id": self.message_id})]

    def _end_thinking(self) -> list[AgentEvent]:
        if not self.reasoning_started:
            return []

        self.reasoning_started = False
        return [self._event("thinking.end", {"id": self.reasoning_id})]

    def _process_tool_call(self, delta: dict[str, Any]) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        index = int(delta.get("index", 0))
        state = self.tool_calls.get(index)
        if state is None:
            state = ToolCallState(index=index)
            self.tool_calls[index] = state

        if delta.get("id"):
            state.call_id = delta["id"]
        function = delta.get("function") or {}
        if function.get("name"):
            state.name = function["name"]

        if not state.started:
            state.started = True
            events.append(self._event("tool_call.start", {
                "call_id": state.call_id,
                "name": state.name,
                "index": index,
            }))

        arguments_delta = function.get("arguments")
        if isinstance(arguments_delta, str) and arguments_delta:
            state.arguments += arguments_delta
            events.append(self._event("tool_call.delta", {
                "call_id": state.call_id,
                "index": index,
                "delta": arguments_delta,
            }))
        return events

    @staticmethod
    def _reasoning_delta(delta: dict[str, Any]) -> str | None:
        for key in ("reasoning_content", "reasoning"):
            value = delta.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _parse_arguments(raw: str) -> Any:
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {"_raw": raw, "_parse_error": True}

    def _event(self, event_type: str, data: dict[str, Any]) -> AgentEvent:
        envelope = dict(data)
        if self.run_id is not None:
            envelope["run_id"] = self.run_id
        if self.step_id is not None:
            envelope["step_id"] = self.step_id
        return AgentEvent(event_type, envelope)
