import re
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from pydantic import BaseModel

from app.core.permissions import Permission
from app.tools.context import ReadScope
from app.tools.contracts import ToolDescription
from app.tools.errors import ToolError


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    version: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    required_permission: Permission
    classification: str
    timeout_seconds: float
    max_result_bytes: int
    handler: Callable[[BaseModel, ReadScope], BaseModel | dict]

    def __post_init__(self):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.name) or not re.fullmatch(
            r"[0-9]+\.[0-9]+", self.version
        ):
            raise ValueError("Invalid stable tool name/version")
        if (
            self.classification != "read"
            or not 0 < self.timeout_seconds <= 5
            or not 128 <= self.max_result_bytes <= 65536
        ):
            raise ValueError("Only bounded read tools may be registered")
        for model in (self.input_model, self.output_model):
            if (
                not model.model_config.get("strict")
                or model.model_config.get("extra") != "forbid"
            ):
                raise ValueError("Tool schemas must be strict and forbid extra fields")

    def describe(self) -> ToolDescription:
        return ToolDescription(
            name=self.name,
            version=self.version,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
            required_permission=self.required_permission,
            classification="read",
            timeout_seconds=float(self.timeout_seconds),
            max_result_bytes=self.max_result_bytes,
        )


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition]):
        tools = {}
        for definition in definitions:
            if definition.name in tools:
                raise ValueError("Duplicate tool name")
            tools[definition.name] = definition
        self._tools = MappingProxyType(tools)

    def resolve(self, name: str, version: str) -> ToolDefinition:
        if name not in self._tools:
            raise ToolError("unknown_tool")
        definition = self._tools[name]
        if version != definition.version:
            raise ToolError("unsupported_version")
        return definition

    def available(self, permissions: frozenset[Permission]) -> list[ToolDescription]:
        return [
            item.describe()
            for _, item in sorted(self._tools.items())
            if item.required_permission in permissions
        ]
