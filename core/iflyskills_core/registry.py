"""Load and model the canonical skill manifest (skills.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import yaml

# core/iflyskills_core/registry.py -> repo root is two parents up (core/ -> root).
_PKG_DIR = Path(__file__).resolve().parent
_CORE_DIR = _PKG_DIR.parent
_DEFAULT_MANIFEST = _CORE_DIR / "skills.yaml"


def repo_root() -> Path:
    """Absolute path to the iFly-Skills repository root.

    Override with IFLY_SKILLS_ROOT when the skill scripts live elsewhere
    (e.g. copied into a container image at a different prefix).
    """
    override = os.environ.get("IFLY_SKILLS_ROOT")
    if override:
        return Path(override).resolve()
    return _CORE_DIR.parent


@dataclass
class SkillArg:
    name: str
    flag: Optional[str] = None  # None => positional argument
    type: str = "string"  # string | integer | number | boolean | enum
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    description: str = ""
    is_output_path: bool = False

    @property
    def is_positional(self) -> bool:
        return self.flag is None


@dataclass
class SkillEntry:
    script: str  # path relative to repo root
    subcommand: Optional[str] = None

    def script_path(self) -> Path:
        return repo_root() / self.script


@dataclass
class Skill:
    id: str
    tool_name: str
    summary: str
    entry: SkillEntry
    cred_profile: str  # xfei | xfyun | ifly | composite | none
    output: str  # stdout_text | file | json | async_task
    advanced: bool = False
    args: List[SkillArg] = field(default_factory=list)

    def arg(self, name: str) -> Optional[SkillArg]:
        return next((a for a in self.args if a.name == name), None)

    @property
    def output_path_arg(self) -> Optional[SkillArg]:
        return next((a for a in self.args if a.is_output_path), None)


def _parse_skill(raw: dict) -> Skill:
    entry_raw = raw["entry"]
    entry = SkillEntry(
        script=entry_raw["script"],
        subcommand=entry_raw.get("subcommand"),
    )
    args = [
        SkillArg(
            name=a["name"],
            flag=a.get("flag"),
            type=a.get("type", "string"),
            required=a.get("required", False),
            default=a.get("default"),
            enum=a.get("enum"),
            description=a.get("description", ""),
            is_output_path=a.get("is_output_path", False),
        )
        for a in raw.get("args", [])
    ]
    return Skill(
        id=raw["id"],
        tool_name=raw["tool_name"],
        summary=raw["summary"],
        entry=entry,
        cred_profile=raw.get("cred_profile", "none"),
        output=raw.get("output", "stdout_text"),
        advanced=raw.get("advanced", False),
        args=args,
    )


def load_registry(manifest: Optional[os.PathLike] = None) -> List[Skill]:
    """Parse skills.yaml into a list of Skill objects.

    Tool names must be unique; a duplicate raises ValueError early so a
    misconfigured manifest fails loudly rather than silently shadowing a tool.
    """
    path = Path(manifest) if manifest else _DEFAULT_MANIFEST
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    skills = [_parse_skill(item) for item in data["skills"]]

    seen: set[str] = set()
    for skill in skills:
        if skill.tool_name in seen:
            raise ValueError(f"Duplicate tool_name in manifest: {skill.tool_name}")
        seen.add(skill.tool_name)
    return skills


def get_skill(tool_name: str, manifest: Optional[os.PathLike] = None) -> Skill:
    for skill in load_registry(manifest):
        if skill.tool_name == tool_name:
            return skill
    raise KeyError(f"Unknown skill tool_name: {tool_name}")
