from semantic_agent.sse_parser import parse_sse_lines


def test_parse_openai_sse_lines_and_done():
    lines = [
        'data: {"choices":[{"delta":{"content":"hi"}}]}',
        '',
        'data: [DONE]',
    ]
    result = list(parse_sse_lines(lines))
    assert result == [{"choices": [{"delta": {"content": "hi"}}]}]
