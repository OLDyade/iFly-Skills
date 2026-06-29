"""MCP server exposing every iFly-Skill as a tool.

Tools and their input schemas are generated from the shared core registry, so
adding a skill to skills.yaml automatically exposes it here — no code change.

Credentials are read from the process environment (canonical names
IFLYTEK_APP_ID / IFLYTEK_API_KEY / IFLYTEK_API_SECRET). Smithery/Glama inject
them from the user's saved configuration.
"""

from __future__ import annotations

import asyncio
import base64
import os

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from iflyskills_core import load_registry, run_skill, to_input_schema
from iflyskills_core.credentials import CredentialError

SERVER_NAME = "iflyskills"

server: Server = Server(SERVER_NAME)


def _skills():
    return load_registry()


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=skill.tool_name,
            description=skill.summary,
            inputSchema=to_input_schema(skill),
        )
        for skill in _skills()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
    try:
        # run_skill spawns a subprocess; keep the event loop responsive.
        result = await asyncio.to_thread(run_skill, name, arguments or {})
    except CredentialError as exc:
        return [types.TextContent(type="text", text=f"Credential error: {exc}")]
    except KeyError as exc:
        return [types.TextContent(type="text", text=f"Unknown tool: {exc}")]

    blocks: list[types.ContentBlock] = []
    if result.stdout.strip():
        blocks.append(types.TextContent(type="text", text=result.stdout.strip()))

    if result.artifact_path:
        note = f"Saved artifact to {result.artifact_path}"
        blocks.append(types.TextContent(type="text", text=note))
        if result.artifact_bytes:
            b64 = base64.b64encode(result.artifact_bytes).decode("ascii")
            blocks.append(
                types.EmbeddedResource(
                    type="resource",
                    resource=types.BlobResourceContents(
                        uri=f"file://{result.artifact_path}",
                        blob=b64,
                        mimeType="application/octet-stream",
                    ),
                )
            )

    if not result.ok:
        err = result.stderr.strip() or f"exited with code {result.returncode}"
        blocks.append(types.TextContent(type="text", text=f"[error] {err}"))

    if not blocks:
        blocks.append(types.TextContent(type="text", text="(no output)"))
    return blocks


async def _run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Console entrypoint. Defaults to stdio transport."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport != "stdio":
        raise SystemExit(
            f"Unsupported MCP_TRANSPORT={transport!r}; this server speaks stdio."
        )
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
