"""Basic MCP-style tool registry: registration + discovery.
NOTE: simplified teaching version, NOT the full Model Context Protocol."""
from dataclasses import dataclass
from typing import Callable

from core.exceptions import PermanentToolError


@dataclass
class ToolSpec:
    name: str
    func: Callable
    description: str
    input_schema: dict


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, func, description, input_schema=None):
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        self._tools[name] = ToolSpec(name, func, description, input_schema or {})

    def discover(self):
        """Tool discovery: what tools exist and how are they called?"""
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in self._tools.values()]

    def get(self, name):
        if name not in self._tools:
            raise PermanentToolError(f"Tool '{name}' is not registered")
        return self._tools[name]

    def names(self):
        return list(self._tools)
