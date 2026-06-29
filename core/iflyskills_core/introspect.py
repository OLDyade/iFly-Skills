"""Best-effort argparse introspection used to CI-validate skills.yaml.

Some skill scripts expose a `build_parser()` function (e.g. iflytek-hyper-tts).
For those, we import the module and read the real argparse definition, then
confirm the manifest hasn't drifted from the script. Scripts that build their
parser inline inside main() cannot be introspected without executing them, so
they are reported as "uncheckable" and rely on the manifest directly.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional

from .registry import Skill, load_registry, repo_root


def _import_module(script_path: Path):
    spec = importlib.util.spec_from_file_location(
        f"_iflyskill_{script_path.stem}", script_path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # may raise ImportError if deps missing
    return module


def extract_flags(script_path: Path) -> Optional[List[str]]:
    """Return all option strings + positional dests from a script's build_parser,
    or None when the script cannot be introspected."""
    try:
        module = _import_module(script_path)
    except Exception:
        return None
    if module is None or not hasattr(module, "build_parser"):
        return None

    parser: argparse.ArgumentParser = module.build_parser()
    flags: List[str] = []
    for action in parser._actions:  # noqa: SLF001 - argparse has no public API
        if action.option_strings:
            flags.extend(action.option_strings)
        elif action.dest != "help":
            flags.append(action.dest)
    return flags


def validate_skill(skill: Skill) -> Dict[str, object]:
    """Check that every flag the manifest declares exists in the real parser."""
    flags = extract_flags(skill.entry.script_path())
    if flags is None:
        return {"tool_name": skill.tool_name, "checked": False, "missing": []}

    missing: List[str] = []
    for arg in skill.args:
        token = arg.flag if arg.flag else arg.name
        # Positional dests in argparse use underscores; manifest names match.
        if arg.flag and arg.flag not in flags:
            missing.append(arg.flag)
        elif not arg.flag and arg.name not in flags:
            missing.append(arg.name)
    return {"tool_name": skill.tool_name, "checked": True, "missing": missing}


def validate_manifest() -> List[Dict[str, object]]:
    return [validate_skill(s) for s in load_registry()]


if __name__ == "__main__":  # pragma: no cover - manual / CI entrypoint
    import sys

    failures = 0
    for report in validate_manifest():
        status = "skip" if not report["checked"] else ("FAIL" if report["missing"] else "ok")
        print(f"[{status:4}] {report['tool_name']}  missing={report['missing']}")
        if report["checked"] and report["missing"]:
            failures += 1
    print(f"\nrepo root: {repo_root()}")
    sys.exit(1 if failures else 0)
