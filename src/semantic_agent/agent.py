from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

from .events import AgentEvent
from .stream_adapter import ChatCompletionStreamAdapter, ToolCallState
from .tools import ToolRegistry


class AgentRuntime:
    def __init__(self, llm_client, tool_registry: ToolRegistry, max_rounds: int = 8):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_rounds = max_rounds

    def run(
        self,
        messages: list[dict[str, Any]],
        extra_body: dict[str, Any] | None = None,
        tool_approval=None,
    ) -> Iterator[AgentEvent]:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        working_messages = [dict(m) for m in messages]

        yield AgentEvent("run.start", {"run_id": run_id})

        try:
            for round_no in range(1, self.max_rounds + 1):
                step_id = f"step_{round_no}"
                adapter = ChatCompletionStreamAdapter(run_id=run_id, step_id=step_id)
                yield AgentEvent("step.start", {"run_id": run_id, "step_id": step_id, "round": round_no})

                final_finish_reason: str | None = None
                saw_chunk = False

                for chunk in self.llm_client.stream_chat(
                    messages=working_messages,
                    tools=self.tool_registry.schemas() or None,
                    extra_body=extra_body,
                ):
                    saw_chunk = True
                    for event in adapter.process(chunk):
                        yield event
                    for choice in chunk.get("choices") or []:
                        if choice.get("finish_reason"):
                            final_finish_reason = choice["finish_reason"]

                if not saw_chunk:
                    raise RuntimeError("LLM stream ended without any data")

                # finalize() is idempotent for already-ended states
                for event in adapter.finalize():
                    yield event

                # No tool call -> current answer is complete.
                if final_finish_reason != "tool_calls" and not adapter.tool_calls:
                    yield AgentEvent("step.end", {
                        "run_id": run_id,
                        "step_id": step_id,
                        "finish_reason": final_finish_reason or "stop",
                    })
                    yield AgentEvent("run.end", {"run_id": run_id, "status": "completed"})
                    return

                # Tool call turn: append the assistant's complete tool calls first.
                assistant_tool_calls = []
                for state in adapter.tool_calls.values():
                    assistant_tool_calls.append({
                        "id": state.call_id,
                        "type": "function",
                        "function": {
                            "name": state.name,
                            "arguments": state.arguments,
                        },
                    })

                if not assistant_tool_calls:
                    raise RuntimeError("finish_reason=tool_calls but no tool_calls were captured")

                working_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": assistant_tool_calls,
                })

                for state in adapter.tool_calls.values():
                    if tool_approval:
                        yield AgentEvent("tool_approval.request", {
                            "run_id": run_id,
                            "step_id": step_id,
                            "call_id": state.call_id,
                            "name": state.name,
                            "arguments": _safe_parse_arguments(state.arguments),
                        })
                        approved = tool_approval(run_id, state.call_id)
                    else:
                        approved = True

                    if not approved:
                        result = {"error": "Tool execution was rejected by the user."}
                        tool_error = "Tool execution was rejected by the user."
                        working_messages.append({
                            "role": "tool",
                            "tool_call_id": state.call_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                        yield AgentEvent("tool_execute.end", {
                            "run_id": run_id,
                            "step_id": step_id,
                            "call_id": state.call_id,
                            "name": state.name,
                            "result": result,
                            "error": tool_error,
                        })
                        continue

                    yield AgentEvent("tool_execute.start", {
                        "run_id": run_id,
                        "step_id": step_id,
                        "call_id": state.call_id,
                        "name": state.name,
                    })
                    try:
                        arguments = _parse_object(state.arguments)
                        if not self.tool_registry.has(state.name or ""):
                            raise KeyError(f"Unknown tool: {state.name}")
                        result = self.tool_registry.execute(state.name or "", arguments)
                        tool_error = None
                    except Exception as exc:  # tool failure must become a tool result
                        result = {"error": str(exc)}
                        tool_error = str(exc)

                    working_messages.append({
                        "role": "tool",
                        "tool_call_id": state.call_id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

                    yield AgentEvent("tool_execute.end", {
                        "run_id": run_id,
                        "step_id": step_id,
                        "call_id": state.call_id,
                        "name": state.name,
                        "result": result,
                        "error": tool_error,
                    })

                yield AgentEvent("step.end", {
                    "run_id": run_id,
                    "step_id": step_id,
                    "finish_reason": "tool_calls",
                })

            raise RuntimeError(f"Maximum agent rounds exceeded: {self.max_rounds}")

        except Exception as exc:
            yield AgentEvent("error", {
                "run_id": run_id,
                "message": str(exc),
            })
            yield AgentEvent("run.end", {"run_id": run_id, "status": "failed"})


def _parse_object(raw: str) -> dict[str, Any]:
    value = json.loads(raw) if raw else {}
    if not isinstance(value, dict):
        raise ValueError("Tool arguments must be a JSON object")
    return value


def _safe_parse_arguments(raw: str) -> dict[str, Any] | None:
    try:
        return _parse_object(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
