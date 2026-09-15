"""Thread-safe coordination for user approval of tool execution."""

from __future__ import annotations

import threading


class ToolApprovalCoordinator:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._decisions: dict[tuple[str, str], bool] = {}

    def wait(self, run_id: str, call_id: str, timeout: float = 300.0) -> bool:
        key = (run_id, call_id)
        with self._condition:
            if key not in self._decisions:
                self._condition.wait_for(lambda: key in self._decisions, timeout=timeout)
            return self._decisions.pop(key, False)

    def decide(self, run_id: str, call_id: str, approved: bool) -> None:
        with self._condition:
            self._decisions[(run_id, call_id)] = approved
            self._condition.notify_all()
