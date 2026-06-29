"""Tests for the IM command router parsing (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bots.router import COMMANDS, parse_command


def test_parse_translate_with_options():
    cmd, payload = parse_command("/translate 你好世界 to=en from=cn")
    assert cmd.tool == "translate"
    assert payload["text"] == "你好世界"
    assert payload["to"] == "en"
    assert payload["from"] == "cn"


def test_parse_plain_text_primary_arg():
    cmd, payload = parse_command("/proofread 这是一段公文")
    assert cmd.tool == "proofread"
    assert payload["text"] == "这是一段公文"


def test_unknown_command_returns_none():
    assert parse_command("/nope hello") is None
    assert parse_command("just chatting") is None


def test_every_command_maps_to_a_tool():
    # Guards against typos between router COMMANDS and the manifest tool names.
    from iflyskills_core import load_registry

    tool_names = {s.tool_name for s in load_registry()}
    for cmd in COMMANDS.values():
        assert cmd.tool in tool_names, cmd.tool
