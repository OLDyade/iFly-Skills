"""Execute an unmodified skill script as a subprocess.

This is the single execution path shared by the MCP server and the FastAPI
backend. n8n shells out to the same scripts directly (Node child_process), but
follows the identical argv + env contract implemented here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .credentials import resolve_env
from .registry import Skill, SkillArg, get_skill


@dataclass
class SkillResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    artifact_path: Optional[str] = None
    artifact_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "ok": self.ok,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
        if self.artifact_path:
            d["artifact_path"] = self.artifact_path
        return d


def _render_value(arg: SkillArg, value: Any) -> List[str]:
    """Render a single argument into argv tokens."""
    if arg.type == "boolean":
        # store_true flags: emit the flag only when truthy.
        return [arg.flag] if value else []
    if arg.is_positional:
        return [str(value)]
    return [arg.flag, str(value)]


def _suffix_for(arg: SkillArg, provided: Optional[Mapping[str, Any]]) -> str:
    fmt = (provided or {}).get("format")
    if isinstance(fmt, str) and fmt and "," not in fmt:
        return f".{fmt}"
    if isinstance(arg.default, str) and "." in arg.default:
        return arg.default[arg.default.rfind("."):]
    return ".bin"


def build_argv(skill: Skill, args: Mapping[str, Any]) -> tuple[List[str], Optional[str]]:
    """Construct the subprocess argv and, for file-output skills, the managed
    output path. Positional args are emitted before optional flags."""
    script = str(skill.entry.script_path())
    argv: List[str] = [sys.executable, script]
    if skill.entry.subcommand:
        argv.append(skill.entry.subcommand)

    managed_output: Optional[str] = None
    positionals: List[str] = []
    options: List[str] = []

    for arg in skill.args:
        if arg.is_output_path:
            value = args.get(arg.name)
            if not value:
                suffix = _suffix_for(arg, args)
                fd, value = tempfile.mkstemp(suffix=suffix, prefix="iflyskill_")
                os.close(fd)
            managed_output = str(value)
            options.extend(_render_value(arg, value))
            continue

        if arg.name not in args or args[arg.name] is None:
            continue  # let the script apply its own default
        tokens = _render_value(arg, args[arg.name])
        (positionals if arg.is_positional else options).extend(tokens)

    argv.extend(positionals)
    argv.extend(options)
    return argv, managed_output


def run_skill(
    tool_name: str,
    args: Mapping[str, Any],
    credentials: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = 600,
    manifest: Optional[os.PathLike] = None,
) -> SkillResult:
    """Run a skill by tool name with the given arguments and credentials.

    `credentials` overrides ambient canonical env vars (IFLYTEK_APP_ID/KEY/SECRET);
    use it to pass per-request credentials without mutating the process env.
    """
    skill = get_skill(tool_name, manifest)
    argv, managed_output = build_argv(skill, args)

    env = dict(os.environ)
    env.update(resolve_env(skill.cred_profile, credentials))
    # Ensure stdout from the child decodes consistently across platforms.
    env.setdefault("PYTHONIOENCODING", "utf-8")

    proc = subprocess.run(
        argv,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

    artifact_bytes: Optional[bytes] = None
    artifact_path: Optional[str] = None
    if skill.output == "file" and managed_output and Path(managed_output).exists():
        artifact_path = managed_output
        artifact_bytes = Path(managed_output).read_bytes()

    return SkillResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        artifact_path=artifact_path,
        artifact_bytes=artifact_bytes,
    )
