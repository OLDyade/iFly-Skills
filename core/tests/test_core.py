"""Unit tests for the shared core: registry, credentials, schema, runner argv."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iflyskills_core import credentials, load_registry, to_input_schema, to_openapi
from iflyskills_core.credentials import CredentialError, resolve_env
from iflyskills_core.registry import get_skill
from iflyskills_core.runner import build_argv


def test_registry_loads_and_tool_names_unique():
    skills = load_registry()
    assert skills, "manifest must not be empty"
    names = [s.tool_name for s in skills]
    assert len(names) == len(set(names))
    # Spot-check a known skill.
    translate = get_skill("translate")
    assert translate.cred_profile == "xfyun"
    assert translate.output == "stdout_text"


@pytest.mark.parametrize(
    "profile,prefix",
    [("xfei", "XFEI"), ("xfyun", "XFYUN"), ("ifly", "IFLY")],
)
def test_resolve_env_maps_canonical_to_prefix(profile, prefix):
    creds = {
        "IFLYTEK_APP_ID": "app",
        "IFLYTEK_API_KEY": "key",
        "IFLYTEK_API_SECRET": "secret",
    }
    env = resolve_env(profile, creds)
    assert env == {
        f"{prefix}_APP_ID": "app",
        f"{prefix}_API_KEY": "key",
        f"{prefix}_API_SECRET": "secret",
    }


def test_resolve_env_composite_falls_back_to_generic_key():
    env = resolve_env(
        "composite",
        {
            "IFLYTEK_APP_ID": "a",
            "IFLYTEK_API_KEY": "k",
            "IFLYTEK_API_SECRET": "s",
        },
    )
    assert env == {
        "LLM_API_KEY": "k",
        "OCR_API_KEY": "k",
        "TRANSLATE_API_KEY": "k",
    }


def test_resolve_env_missing_credentials_raises():
    with pytest.raises(CredentialError):
        resolve_env("xfei", {})


def test_resolve_env_none_profile_is_empty():
    assert resolve_env("none", {}) == {}


def test_input_schema_excludes_output_path_and_marks_required():
    tts = get_skill("hyper_tts")
    schema = to_input_schema(tts)
    assert "output" not in schema["properties"]  # managed by runner
    assert schema["properties"]["sample_rate"]["enum"] == [8000, 16000, 24000]
    assert schema["properties"]["sample_rate"]["type"] == "integer"

    img = get_skill("image_understanding")
    assert "image" in to_input_schema(img)["required"]


def test_openapi_has_single_post_path():
    doc = to_openapi(get_skill("translate"))
    assert doc["openapi"].startswith("3.0")
    assert "/skills/translate" in doc["paths"]
    assert "post" in doc["paths"]["/skills/translate"]


def test_build_argv_positionals_before_options():
    skill = get_skill("translate")
    argv, managed = build_argv(skill, {"text": "hello", "to_lang": "en", "raw": True})
    assert managed is None
    # script path then positional 'hello' then options
    assert argv[1].endswith("translate.py")
    assert "hello" in argv
    assert "--to" in argv and "en" in argv
    assert "--raw" in argv  # boolean flag present without a value
    assert argv.index("hello") < argv.index("--to")


def test_build_argv_boolean_false_omitted():
    skill = get_skill("translate")
    argv, _ = build_argv(skill, {"text": "hi", "raw": False})
    assert "--raw" not in argv


def test_build_argv_file_output_is_managed():
    skill = get_skill("hyper_tts")
    argv, managed = build_argv(skill, {"text": "你好"})
    assert managed is not None
    assert "--output" in argv
    assert managed in argv


def test_build_argv_subcommand_first():
    skill = get_skill("voiceclone_synth")
    argv, _ = build_argv(skill, {"text": "hi", "res_id": "r1"})
    # python script.py synth <text> --res-id r1 --output <managed>
    assert argv[2] == "synth"
    assert "--res-id" in argv and "r1" in argv
