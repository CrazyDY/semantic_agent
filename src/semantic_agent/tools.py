from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class RegisteredTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        self._tools[name] = RegisteredTool(name, description, parameters, handler)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(**arguments)

    def has(self, name: str) -> bool:
        return name in self._tools


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def get_weather(city: str) -> dict[str, Any]:
        # Demo tool only. Replace with your real business/API call.
        demo = {
            "Beijing": {"temperature": 28, "condition": "晴"},
            "Shanghai": {"temperature": 30, "condition": "多云"},
            "Singapore": {"temperature": 31, "condition": "雷阵雨"},
        }
        return {"city": city, **demo.get(city, {"temperature": None, "condition": "未知"})}

    registry.register(
        name="get_weather",
        description="查询指定城市当前的演示天气信息",
        parameters={
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名称"}},
            "required": ["city"],
            "additionalProperties": False,
        },
        handler=get_weather,
    )
    return registry
