"""Render a Skill manifest into JSON Schema (MCP inputSchema) and OpenAPI 3.0.

Both distribution formats are derived from the same manifest so a tool's
interface can never drift between the MCP server (#43) and the Coze plugin (#44).
"""

from __future__ import annotations

from typing import Any, Dict

from .registry import Skill, SkillArg

_JSON_TYPES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "enum": "string",  # refined below via `enum`
}


def _property_for(arg: SkillArg) -> Dict[str, Any]:
    prop: Dict[str, Any] = {"type": _JSON_TYPES.get(arg.type, "string")}
    if arg.enum is not None:
        # Enum values keep their native type (e.g. integer sample rates).
        prop["enum"] = arg.enum
        if all(isinstance(v, bool) for v in arg.enum):
            prop["type"] = "boolean"
        elif all(isinstance(v, int) for v in arg.enum):
            prop["type"] = "integer"
        elif all(isinstance(v, (int, float)) for v in arg.enum):
            prop["type"] = "number"
        else:
            prop["type"] = "string"
    if arg.description:
        prop["description"] = arg.description
    if arg.default is not None:
        prop["default"] = arg.default
    return prop


def to_input_schema(skill: Skill) -> Dict[str, Any]:
    """JSON Schema object describing the tool's arguments (MCP inputSchema)."""
    properties: Dict[str, Any] = {}
    required = []
    for arg in skill.args:
        # The output-file path is managed by the runner, not the caller.
        if arg.is_output_path:
            continue
        properties[arg.name] = _property_for(arg)
        if arg.required:
            required.append(arg.name)

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def to_openapi(skill: Skill, server_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """A standalone OpenAPI 3.0 document for one skill (Coze: one tool per schema)."""
    path = f"/skills/{skill.tool_name}"
    return {
        "openapi": "3.0.1",
        "info": {
            "title": f"iFLYTEK {skill.tool_name}",
            "description": skill.summary,
            "version": "1.0.0",
        },
        "servers": [{"url": server_url}],
        "paths": {
            path: {
                "post": {
                    "operationId": skill.tool_name,
                    "summary": skill.summary,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": to_input_schema(skill),
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Skill result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "boolean"},
                                            "output": {"type": "string"},
                                            "artifact_url": {"type": "string"},
                                            "task_id": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }
