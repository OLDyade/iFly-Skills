"""FastAPI app exposing every skill as POST /skills/{tool_name}.

Routes are generated from the shared core registry. Text results are returned
inline; media artifacts are persisted and returned as a downloadable URL so
Coze and IM clients can fetch them.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from iflyskills_core import load_registry, run_skill
from iflyskills_core.credentials import CredentialError
from iflyskills_core.registry import Skill

ARTIFACT_DIR = Path(os.environ.get("IFLY_ARTIFACT_DIR", "/tmp/iflyskills-artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

app = FastAPI(
    title="iFly-Skills Backend",
    version="1.0.0",
    description="HTTP gateway over iFLYTEK skills, shared by Coze plugins and IM bots.",
)


def _per_request_credentials(request: Request) -> Optional[Dict[str, str]]:
    """Allow callers to pass credentials per request via headers, otherwise the
    server falls back to its own environment."""
    mapping = {
        "X-IFLYTEK-APP-ID": "IFLYTEK_APP_ID",
        "X-IFLYTEK-API-KEY": "IFLYTEK_API_KEY",
        "X-IFLYTEK-API-SECRET": "IFLYTEK_API_SECRET",
    }
    creds = {
        canonical: request.headers[header]
        for header, canonical in mapping.items()
        if header in request.headers
    }
    return creds or None


def _artifact_url(request: Request, filename: str) -> str:
    base = PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return f"{base}/artifacts/{filename}"


def _make_handler(skill: Skill):
    async def handler(request: Request) -> JSONResponse:
        try:
            payload: Dict[str, Any] = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")

        try:
            result = run_skill(
                skill.tool_name,
                payload,
                credentials=_per_request_credentials(request),
            )
        except CredentialError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

        body: Dict[str, Any] = {"ok": result.ok}
        if result.stdout.strip():
            body["output"] = result.stdout.strip()
        if not result.ok:
            body["error"] = result.stderr.strip() or f"exit {result.returncode}"

        if result.artifact_bytes:
            suffix = Path(result.artifact_path or "out.bin").suffix or ".bin"
            filename = f"{uuid.uuid4().hex}{suffix}"
            (ARTIFACT_DIR / filename).write_bytes(result.artifact_bytes)
            body["artifact_url"] = _artifact_url(request, filename)

        return JSONResponse(body, status_code=200 if result.ok else 502)

    return handler


def _register_routes() -> None:
    for skill in load_registry():
        app.add_api_route(
            f"/skills/{skill.tool_name}",
            _make_handler(skill),
            methods=["POST"],
            name=skill.tool_name,
            summary=skill.summary,
            tags=["skills"],
        )


_register_routes()


@app.get("/artifacts/{filename}")
async def get_artifact(filename: str) -> FileResponse:
    # Reject path traversal; only serve flat names from the artifact dir.
    safe = Path(filename).name
    path = ARTIFACT_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path)


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {"ok": True, "skills": [s.tool_name for s in load_registry()]}


# IM bot webhooks (#46). The Feishu and WeCom adapters are HTTP-based and mount
# here; DingTalk uses an outbound Stream connection (run bots.dingtalk separately).
def _mount_bots() -> None:
    try:
        from bots.feishu import router as feishu_router
        from bots.wecom import router as wecom_router
    except Exception:  # pragma: no cover - bots optional at import time
        return
    app.include_router(feishu_router)
    app.include_router(wecom_router)


_mount_bots()
