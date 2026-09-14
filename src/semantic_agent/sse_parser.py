from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any


def parse_sse_lines(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Parse OpenAI-compatible SSE lines into JSON payloads.

    Supports comments, blank lines, optional multi-line data fields and [DONE].
    """
    data_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")

        if not line:
            if data_lines:
                yield from _parse_data_lines(data_lines)
                data_lines = []
            continue

        if line.startswith(":"):
            continue

        if line.startswith("data:"):
            value = line[5:]
            if value.startswith(" "):
                value = value[1:]
            data_lines.append(value)

    if data_lines:
        yield from _parse_data_lines(data_lines)


def _parse_data_lines(data_lines: list[str]) -> Iterator[dict[str, Any]]:
    payload = "\n".join(data_lines).strip()
    if not payload or payload == "[DONE]":
        return
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return
    if isinstance(parsed, dict):
        yield parsed
