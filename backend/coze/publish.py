"""Create / publish Coze plugins from the per-skill OpenAPI schemas.

Coze hosts two clouds with identical APIs on different domains:
  * Global : https://api.coze.com
  * China  : https://api.coze.cn

Each skill becomes one plugin registered from its OpenAPI 3.0 document (the
files emitted by app.openapi_export). The plugin endpoint paths below follow
the documented `/v1/plugin/*` surface; override with --create-path /
--publish-path if your account exposes a different version.

Auth: a Personal Access Token in COZE_API_TOKEN (or --token).

    python -m coze.publish --region cn --workspace-id 123 --openapi-dir openapi
    python -m coze.publish --region com --dry-run            # print payloads only
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

import requests

BASE_URLS = {
    "com": "https://api.coze.com",
    "cn": "https://api.coze.cn",
}


def _load_schemas(openapi_dir: Path) -> Dict[str, Dict[str, Any]]:
    schemas = {}
    for path in sorted(openapi_dir.glob("*.json")):
        schemas[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    if not schemas:
        raise SystemExit(f"No OpenAPI schemas found in {openapi_dir}")
    return schemas


def _create_payload(tool_name: str, schema: Dict[str, Any], workspace_id: str) -> Dict[str, Any]:
    info = schema.get("info", {})
    return {
        "workspace_id": workspace_id,
        "name": info.get("title", tool_name),
        "description": info.get("description", ""),
        "openapi": schema,
        "auth": {"type": "none"},
    }


def publish(
    region: str,
    workspace_id: str,
    openapi_dir: Path,
    token: str,
    dry_run: bool,
    create_path: str,
    publish_path: str,
) -> None:
    base = BASE_URLS[region]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    schemas = _load_schemas(openapi_dir)

    for tool_name, schema in schemas.items():
        payload = _create_payload(tool_name, schema, workspace_id)
        if dry_run:
            print(f"--- {tool_name} -> POST {base}{create_path} ---")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            continue

        resp = requests.post(base + create_path, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        plugin_id = resp.json().get("data", {}).get("plugin_id")
        print(f"created {tool_name}: plugin_id={plugin_id}")

        if plugin_id and publish_path:
            pub = requests.post(
                base + publish_path,
                headers=headers,
                json={"plugin_id": plugin_id},
                timeout=30,
            )
            pub.raise_for_status()
            print(f"published {tool_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", choices=["com", "cn"], default="cn")
    parser.add_argument("--workspace-id", default=os.environ.get("COZE_WORKSPACE_ID", ""))
    parser.add_argument(
        "--openapi-dir",
        default=str(Path(__file__).resolve().parent.parent / "openapi"),
    )
    parser.add_argument("--token", default=os.environ.get("COZE_API_TOKEN", ""))
    parser.add_argument("--create-path", default="/v1/plugin/create")
    parser.add_argument("--publish-path", default="/v1/plugin/publish")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads; make no API calls.")
    args = parser.parse_args()

    if not args.dry_run:
        if not args.token:
            raise SystemExit("COZE_API_TOKEN (or --token) is required unless --dry-run")
        if not args.workspace_id:
            raise SystemExit("--workspace-id (or COZE_WORKSPACE_ID) is required unless --dry-run")

    publish(
        region=args.region,
        workspace_id=args.workspace_id,
        openapi_dir=Path(args.openapi_dir),
        token=args.token,
        dry_run=args.dry_run,
        create_path=args.create_path,
        publish_path=args.publish_path,
    )


if __name__ == "__main__":
    main()
