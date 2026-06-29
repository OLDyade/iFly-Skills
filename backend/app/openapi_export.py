"""Generate one OpenAPI 3.0 document per skill (Coze: one tool per schema).

Usage:
    python -m app.openapi_export --server-url https://your-host --out openapi
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from iflyskills_core import load_registry, to_openapi


def export(server_url: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for skill in load_registry():
        doc = to_openapi(skill, server_url=server_url)
        path = out_dir / f"{skill.tool_name}.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="Public base URL where the backend is reachable (used in servers[]).",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "openapi"),
        help="Output directory for the per-skill OpenAPI JSON files.",
    )
    args = parser.parse_args()
    written = export(args.server_url, Path(args.out))
    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
