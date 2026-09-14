from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests

from .sse_parser import parse_sse_lines


class LLMClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        connect_timeout: float = 10.0,
        read_timeout: float = 300.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = (connect_timeout, read_timeout)
        self.session = session or requests.Session()

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        if extra_body:
            payload.update(extra_body)

        try:
            with self.session.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as response:
                if not response.ok:
                    body = response.text[:2000]
                    raise LLMClientError(f"LLM HTTP {response.status_code}: {body}")

                for chunk in parse_sse_lines(response.iter_lines(decode_unicode=True)):
                    yield chunk
        except requests.RequestException as exc:
            raise LLMClientError(f"LLM request failed: {exc}") from exc

    def close(self) -> None:
        self.session.close()
