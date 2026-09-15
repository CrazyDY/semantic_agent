"""Tornado implementation of the Semantic Agent HTTP/SSE API.

The FastAPI application remains available in :mod:`semantic_agent.api`.  This
module exposes the same ``/health`` and ``/chat`` endpoints for deployments
that use Tornado instead.
"""

from __future__ import annotations

import tornado.ioloop
import tornado.web
from tornado.escape import json_decode

from .agent import AgentRuntime
from .config import Settings
from .llm_client import OpenAICompatibleClient
from .tools import default_registry

from .tool_approval import ToolApprovalCoordinator



def build_agent(settings: Settings | None = None) -> AgentRuntime:
    """Create the runtime used by the Tornado application."""
    configured = settings or Settings()
    llm = OpenAICompatibleClient(
        base_url=configured.LLM_BASE_URL,
        api_key=configured.LLM_API_KEY,
        model=configured.LLM_MODEL,
        connect_timeout=configured.LLM_CONNECT_TIMEOUT,
        read_timeout=configured.LLM_READ_TIMEOUT,
    )
    return AgentRuntime(llm, default_registry(), max_rounds=configured.AGENT_MAX_ROUNDS)


class HealthHandler(tornado.web.RequestHandler):
    def initialize(self, settings: Settings) -> None:
        self.agent_settings = settings

    def get(self) -> None:
        self.set_header("Content-Type", "application/json")
        self.write({"ok": True, "model": self.agent_settings.LLM_MODEL, "base_url": self.agent_settings.LLM_BASE_URL})


class ChatHandler(tornado.web.RequestHandler):

    def initialize(self, agent: AgentRuntime, approvals: ToolApprovalCoordinator) -> None:
        self.agent = agent
        self.approvals = approvals


    async def post(self) -> None:
        try:
            payload = json_decode(self.request.body)
        except ValueError:
            self.send_error(400, reason="Request body must be valid JSON")
            return

        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list) or not payload["messages"]:
            self.send_error(400, reason="messages must be a non-empty array")
            return
        if not all(isinstance(message, dict) for message in payload["messages"]):
            self.send_error(400, reason="each message must be an object")
            return
        extra_body = payload.get("extra_body")
        if extra_body is not None and not isinstance(extra_body, dict):
            self.send_error(400, reason="extra_body must be an object")
            return

        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        self.set_header("X-Accel-Buffering", "no")

        # AgentRuntime yields already-serialized semantic event payloads, so
        # this endpoint intentionally accepts both plain text and multimodal
        # OpenAI-compatible content arrays without transforming them.

        event_iterator = iter(self.agent.run(payload["messages"], extra_body, self.approvals.wait))
        while True:
            # The synchronous LLM stream may wait for a user decision. Pulling
            # it in a worker keeps Tornado's IOLoop free to receive the
            # corresponding /tool-approvals request.
            event = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, _next_event, event_iterator,
            )
            if event is None:
                break

            if self.request.connection.stream.closed():
                break
            self.write(event.to_sse())
            await self.flush()



class ToolApprovalHandler(tornado.web.RequestHandler):
    def initialize(self, approvals: ToolApprovalCoordinator) -> None:
        self.approvals = approvals

    def post(self) -> None:
        try:
            payload = json_decode(self.request.body)
            run_id = payload["run_id"]
            call_id = payload["call_id"]
            approved = payload["approved"]
        except (KeyError, TypeError, ValueError):
            self.send_error(400, reason="run_id, call_id, and approved are required")
            return
        if not isinstance(run_id, str) or not isinstance(call_id, str) or not isinstance(approved, bool):
            self.send_error(400, reason="run_id/call_id must be strings and approved must be a boolean")
            return
        self.set_header("Content-Type", "application/json")
        self.approvals.decide(run_id, call_id, approved)
        self.write({"ok": True})


def _next_event(event_iterator):
    try:
        return next(event_iterator)
    except StopIteration:
        return None




def create_application(
    agent: AgentRuntime | None = None,
    settings: Settings | None = None,
) -> tornado.web.Application:
    """Build an application with API routes equivalent to the FastAPI app."""
    configured = settings or Settings()
    runtime = agent or build_agent(configured)

    approvals = ToolApprovalCoordinator()
    return tornado.web.Application([
        (r"/health", HealthHandler, {"settings": configured}),
        (r"/chat", ChatHandler, {"agent": runtime, "approvals": approvals}),
        (r"/tool-approvals", ToolApprovalHandler, {"approvals": approvals}),

    ])


def main() -> None:
    app = create_application()
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
