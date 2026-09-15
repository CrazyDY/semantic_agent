from __future__ import annotations

import threading
import time

from semantic_agent.tool_approval import ToolApprovalCoordinator


def test_tool_approval_coordinator_returns_submitted_decision():
    coordinator = ToolApprovalCoordinator()
    decision: list[bool] = []

    waiter = threading.Thread(
        target=lambda: decision.append(coordinator.wait("run_1", "call_1", timeout=1)),
    )
    waiter.start()
    time.sleep(0.01)
    coordinator.decide("run_1", "call_1", True)
    waiter.join(timeout=1)

    assert decision == [True]


def test_tool_approval_coordinator_rejects_when_it_times_out():
    coordinator = ToolApprovalCoordinator()

    assert coordinator.wait("run_1", "call_1", timeout=0.001) is False
