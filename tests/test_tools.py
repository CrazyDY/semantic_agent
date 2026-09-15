from __future__ import annotations

from semantic_agent.tools import FileSystemTools, ShellTools, default_registry


def test_file_system_tools_support_normal_file_operations(tmp_path):
    tools = FileSystemTools(tmp_path)

    assert tools.create_directory("notes") == {"path": "notes"}
    assert tools.write_file("notes/todo.txt", "first") == {"path": "notes/todo.txt", "bytes_written": 5}
    tools.write_file("notes/todo.txt", " second", append=True)
    assert tools.read_file("notes/todo.txt")["content"] == "first second"
    assert tools.list_files("notes")["entries"] == ["notes/todo.txt"]

    tools.copy_path("notes/todo.txt", "copy.txt")
    assert tools.read_file("copy.txt")["content"] == "first second"
    assert tools.move_path("copy.txt", "moved.txt") == {"source": "copy.txt", "destination": "moved.txt"}
    assert tools.delete_path("moved.txt") == {"path": "moved.txt"}


def test_file_system_tools_reject_paths_outside_workspace(tmp_path):
    tools = FileSystemTools(tmp_path)

    try:
        tools.write_file("../outside.txt", "not allowed")
    except ValueError as error:
        assert "workspace" in str(error)
    else:
        raise AssertionError("Expected a workspace-boundary error")


def test_file_system_tools_use_relative_to_compatible_boundary_check(tmp_path):
    tools = FileSystemTools(tmp_path)

    assert tools._is_within_workspace(tmp_path / "inside.txt") is True
    assert tools._is_within_workspace(tmp_path.parent / "outside.txt") is False


def test_file_system_tools_require_recursive_deletion_for_directories(tmp_path):
    tools = FileSystemTools(tmp_path)
    tools.write_file("nested/file.txt", "content")

    try:
        tools.delete_path("nested")
    except ValueError as error:
        assert "recursive=true" in str(error)
    else:
        raise AssertionError("Expected a recursive-deletion error")

    assert tools.delete_path("nested", recursive=True) == {"path": "nested"}


def test_shell_tool_runs_in_workspace_and_captures_exit_status(tmp_path):
    result = ShellTools(tmp_path).run_shell_command("pwd && printf hello && exit 3")

    assert result["exit_code"] == 3
    assert result["stdout"].endswith("hello")
    assert str(tmp_path) in result["stdout"]
    assert result["timed_out"] is False


def test_default_registry_exposes_file_and_shell_tools(tmp_path):
    registry = default_registry(tmp_path)

    assert {"read_file", "write_file", "list_files", "create_directory", "move_path", "copy_path", "delete_path", "run_shell_command"} <= {
        schema["function"]["name"] for schema in registry.schemas()
    }
    registry.execute("write_file", {"path": "answer.txt", "content": "42"})
    assert registry.execute("read_file", {"path": "answer.txt"})["content"] == "42"
