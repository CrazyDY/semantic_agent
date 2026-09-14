from __future__ import annotations

import json

from tornado.testing import AsyncHTTPTestCase

from semantic_agent.events import AgentEvent
from semantic_agent.tornado_api import create_application


class FakeAgent:
    def __init__(self) -> None:
        self.requests: list[tuple[list[dict], dict | None]] = []

    def run(self, messages: list[dict], extra_body: dict | None = None):
        self.requests.append((messages, extra_body))
        yield AgentEvent("run.start", {"run_id": "run_test"})
        yield AgentEvent("run.end", {"run_id": "run_test", "status": "completed"})


class TornadoApiTest(AsyncHTTPTestCase):
    def get_app(self):
        self.agent = FakeAgent()
        return create_application(agent=self.agent)  # type: ignore[arg-type]

    def test_health(self):
        response = self.fetch("/health")

        assert response.code == 200
        assert json.loads(response.body)["ok"] is True

    def test_chat_streams_events_and_forwards_multimodal_content(self):
        content = [
            {"type": "text", "text": "describe this image"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
        ]
        response = self.fetch(
            "/chat",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"messages": [{"role": "user", "content": content}]}),
        )

        assert response.code == 200
        assert response.headers["Content-Type"].startswith("text/event-stream")
        assert b"event: run.start" in response.body
        assert self.agent.requests == [([{"role": "user", "content": content}], None)]

    def test_chat_rejects_invalid_message_payload(self):
        response = self.fetch("/chat", method="POST", body=json.dumps({"messages": []}))

        assert response.code == 400
