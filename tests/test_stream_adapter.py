from semantic_agent.stream_adapter import ChatCompletionStreamAdapter


def ev_types(events):
    return [e.type for e in events]


def test_message_stream_emits_semantic_events():
    adapter = ChatCompletionStreamAdapter()
    events = []
    chunks = [
        {"choices": [{"delta": {"content": "你"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "好"}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ]
    for chunk in chunks:
        events.extend(adapter.process(chunk))

    assert ev_types(events) == [
        "message.start", "message.delta", "message.delta", "message.end"
    ]
    assert "你好" == "".join(e.data.get("delta", "") for e in events if e.type == "message.delta")


def test_reasoning_content_is_adapted():
    adapter = ChatCompletionStreamAdapter()
    events = []
    for chunk in [
        {"choices": [{"delta": {"reasoning_content": "先"}, "finish_reason": None}]},
        {"choices": [{"delta": {"reasoning_content": "分析"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "答案"}, "finish_reason": "stop"}]},
    ]:
        events.extend(adapter.process(chunk))

    assert ev_types(events) == [
        "thinking.start", "thinking.delta", "thinking.delta", "message.start", "message.delta",
        "thinking.end", "message.end"
    ]


def test_tool_call_arguments_are_accumulated_and_completed():
    adapter = ChatCompletionStreamAdapter()
    events = []
    chunks = [
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": ""}}]}, "finish_reason": None}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"city":'}}]}, "finish_reason": None}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"Beijing"}'}}]}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
    ]
    for chunk in chunks:
        events.extend(adapter.process(chunk))

    assert ev_types(events) == ["tool_call.start", "tool_call.delta", "tool_call.delta", "tool_call.end"]
    end = events[-1]
    assert end.data["call_id"] == "call_1"
    assert end.data["name"] == "get_weather"
    assert end.data["arguments"] == {"city": "Beijing"}


def test_multiple_tool_calls_use_index_as_state_key():
    adapter = ChatCompletionStreamAdapter()
    events = []
    chunks = [
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "a", "function": {"name": "one", "arguments": '{"x":1}'}},
            {"index": 1, "id": "b", "function": {"name": "two", "arguments": '{"y":2}'}},
        ]}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
    ]
    for chunk in chunks:
        events.extend(adapter.process(chunk))

    ends = [e for e in events if e.type == "tool_call.end"]
    assert [(e.data["call_id"], e.data["name"]) for e in ends] == [("a", "one"), ("b", "two")]
