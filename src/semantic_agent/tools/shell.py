"""A workspace-scoped shell-command tool."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class ShellTools:
    def __init__(self, workspace_root: str | Path, max_timeout: float = 60.0) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.max_timeout = max_timeout

    def run_shell_command(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        """Run a shell command from the workspace and return its captured output."""
        if not command.strip():
            raise ValueError("command must not be empty")
        if timeout <= 0 or timeout > self.max_timeout:
            raise ValueError(f"timeout must be between 0 and {self.max_timeout:g} seconds")
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "exit_code": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timed_out": True,
            }
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
