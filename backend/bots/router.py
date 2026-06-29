"""Command router shared by every IM platform.

A chat message like:

    /translate 你好世界 to=en
    /tts 今天天气不错
    /proofread 这是一段需要校对的公文

is parsed into a skill tool name + payload, dispatched to the backend HTTP API,
and rendered back into a text reply. Platform adapters (dingtalk/feishu/wecom)
only handle transport + auth; all skill logic lives here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")


@dataclass(frozen=True)
class Command:
    tool: str          # skill tool_name on the backend
    primary_arg: str   # where the free-text portion of the message goes
    usage: str


# Chat command -> skill. Keeps the surface small and text-friendly; richer
# skills (pdf_ocr, voiceclone, video_translate) are intentionally omitted
# because they need file/URL inputs a chat line cannot carry.
COMMANDS: Dict[str, Command] = {
    "translate": Command("translate", "text", "/translate <text> [from=cn] [to=en]"),
    "proofread": Command("proofread", "text", "/proofread <text>"),
    "tts": Command("hyper_tts", "text", "/tts <text> [vcn=...]"),
    "describe": Command("image_understanding", "image", "/describe <image_path> [question=...]"),
    "ocr": Command("image_ocr", "image_path", "/ocr <image_path>"),
}


def _help_text() -> str:
    lines = ["可用指令 / Available commands:"]
    lines += [f"  {cmd.usage}" for cmd in COMMANDS.values()]
    lines.append("  /help")
    return "\n".join(lines)


def parse_command(message: str) -> Optional[Tuple[Command, Dict[str, object]]]:
    """Return (command, payload) or None when the message isn't a known command."""
    text = message.strip()
    if not text.startswith("/"):
        return None
    body = text[1:]
    if not body:
        return None

    name, _, rest = body.partition(" ")
    name = name.lower()
    if name in ("help", ""):
        return None
    command = COMMANDS.get(name)
    if command is None:
        return None

    # Trailing key=value tokens become options; everything else is primary text.
    words = rest.split()
    options: Dict[str, object] = {}
    primary_words = []
    for word in words:
        if "=" in word and not word.startswith("="):
            key, _, value = word.partition("=")
            options[key] = value
        else:
            primary_words.append(word)

    payload: Dict[str, object] = dict(options)
    primary = " ".join(primary_words).strip()
    if primary:
        payload[command.primary_arg] = primary
    return command, payload


def dispatch(message: str, timeout: float = 120) -> str:
    """Route a chat message to the backend and produce a text reply."""
    text = message.strip()
    if text in ("/help", "/", "") or text.lower() == "/help":
        return _help_text()

    parsed = parse_command(text)
    if parsed is None:
        return f"未识别的指令。\n{_help_text()}"

    command, payload = parsed
    if command.primary_arg not in payload and command.tool != "hyper_tts":
        return f"缺少参数。用法: {command.usage}"

    try:
        resp = requests.post(
            f"{BACKEND_URL}/skills/{command.tool}",
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return f"后端请求失败: {exc}"

    data = resp.json() if resp.content else {}
    if not data.get("ok"):
        return f"执行失败: {data.get('error', resp.status_code)}"

    if data.get("artifact_url"):
        return f"已生成: {data['artifact_url']}"
    return str(data.get("output", "(无输出)"))
