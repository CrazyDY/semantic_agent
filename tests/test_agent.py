from semantic_agent.agent import AgentRuntime
from semantic_agent.tools import ToolRegistry


class FakeLLM:
    def __init__(self):
        self.calls = 0
        self.requests = []

    def stream_chat(self, messages, tools=None, extra_body=None):
        self.calls += 1
        self.requests.append(messages.copy())
        if self.calls == 1:
            yield {"choices": [{"delta": {"tool_calls": [
                {"index": 0, "id": "call_1", "type": "function", "function": {"name": "add", "arguments": '{"a":2,"b":3}'}}
            ]}, "finish_reason": None}]}
            yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        else:
            yield {"choices": [{"delta": {"content": "5"}, "finish_reason": None}]}
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}


class ToolExecutorRegistry(ToolRegistry):
    def __init__(self):
        super().__init__()
        self.register(
            "add",
            "add two integers",
            {"type":"object","properties":{"a":{"type":"integer"},"b":{"type":"integer"}},"required":["a","b"]},
            lambda a, b: a + b,
        )


def test_agent_executes_tool_then_calls_llm_again():
    llm = FakeLLM()
    agent = AgentRuntime(llm, ToolExecutorRegistry(), max_rounds=3)
    events = list(agent.run([{"role": "user", "content": "2+3?"}]))
    types = [e.type for e in events]
    assert types == [
        "run.start", "step.start",
        "tool_call.start", "tool_call.delta", "tool_call.end",
        "tool_execute.start", "tool_execute.end",
        "step.end",
        "step.start",
        "message.start", "message.delta", "message.end",
        "step.end", "run.end"
    ]
    assert llm.calls == 2
    assert any(m.get("role") == "tool" for m in llm.requests[1])


def test_agent_forwards_multimodal_user_content_to_the_llm():
    llm = FakeLLM()
    agent = AgentRuntime(llm, ToolExecutorRegistry(), max_rounds=3)
    content = [
        {"type": "text", "text": "这张图片里有什么？"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
    ]

    list(agent.run([{"role": "user", "content": content}]))

    assert llm.requests[0][0]["content"] == content
