"""Shared foundation for distributing iFly-Skills to external ecosystems.

Every distribution channel (MCP server, Coze plugin, IM bots, n8n nodes)
consumes this package: it introspects each skill's CLI into a uniform manifest,
maps a single canonical credential set onto each skill's env vars, and runs the
unmodified skill scripts as subprocesses.
"""

from .registry import Skill, SkillArg, SkillEntry, get_skill, load_registry, repo_root
from .credentials import CredentialError, resolve_env
from .runner import SkillResult, run_skill
from .schema import to_input_schema, to_openapi

__all__ = [
    "Skill",
    "SkillArg",
    "SkillEntry",
    "load_registry",
    "get_skill",
    "repo_root",
    "resolve_env",
    "CredentialError",
    "run_skill",
    "SkillResult",
    "to_input_schema",
    "to_openapi",
]

__version__ = "0.1.0"
