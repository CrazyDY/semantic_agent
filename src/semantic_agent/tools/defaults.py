from __future__ import annotations

from pathlib import Path
from typing import Any

from .filesystem import FileSystemTools
from .registry import ToolRegistry
from .shell import ShellTools


def default_registry(workspace_root: str | Path | None = None) -> ToolRegistry:
    """Create the built-in registry, scoped to ``workspace_root`` (the CWD by default)."""
    registry = ToolRegistry()
    workspace = Path(workspace_root or Path.cwd()).resolve()
    files = FileSystemTools(workspace)
    shell = ShellTools(workspace)

    def get_weather(city: str) -> dict[str, Any]:
        demo = {
            "Beijing": {"temperature": 28, "condition": "晴"},
            "Shanghai": {"temperature": 30, "condition": "多云"},
            "Singapore": {"temperature": 31, "condition": "雷阵雨"},
        }
        return {"city": city, **demo.get(city, {"temperature": None, "condition": "未知"})}

    registry.register("get_weather", "查询指定城市当前的演示天气信息", _object({"city": _string("城市名称")}, ["city"]), get_weather)
    registry.register("read_file", "读取工作区中的 UTF-8 文本文件", _object({"path": _string("相对于工作区的文件路径"), "encoding": _string("文本编码，默认 utf-8")}, ["path"]), files.read_file)
    registry.register("write_file", "在工作区创建或覆盖文本文件；append=true 时追加内容", _object({"path": _string("相对于工作区的文件路径"), "content": _string("写入的文本内容"), "append": {"type": "boolean", "description": "是否追加"}, "encoding": _string("文本编码，默认 utf-8")}, ["path", "content"]), files.write_file)
    registry.register("list_files", "列出工作区中的目录内容", _object({"path": _string("目录路径，默认工作区根目录"), "recursive": {"type": "boolean", "description": "是否递归列出"}}), files.list_files)
    registry.register("create_directory", "在工作区创建目录（包含父目录）", _object({"path": _string("目录路径")}, ["path"]), files.create_directory)
    registry.register("move_path", "移动或重命名工作区中的文件或目录", _object({"source": _string("源路径"), "destination": _string("目标路径")}, ["source", "destination"]), files.move_path)
    registry.register("copy_path", "复制工作区中的文件或目录", _object({"source": _string("源路径"), "destination": _string("目标路径")}, ["source", "destination"]), files.copy_path)
    registry.register("delete_path", "删除工作区中的文件；删除目录必须指定 recursive=true", _object({"path": _string("要删除的路径"), "recursive": {"type": "boolean", "description": "是否递归删除目录"}}, ["path"]), files.delete_path)
    registry.register("run_shell_command", "在工作区根目录执行 shell 命令并返回标准输出、标准错误和退出码", _object({"command": _string("要执行的 shell 命令"), "timeout": {"type": "number", "description": "超时秒数，默认 30，最大 60"}}, ["command"]), shell.run_shell_command)
    return registry


def _string(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema
