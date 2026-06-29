"""Feishu / Lark adapter — event subscription webhook.

Exposes an APIRouter mounted at /feishu. Handles the url_verification challenge
and im.message.receive_v1 events, routes the text through bots.router, and
replies via the Feishu open API (tenant_access_token + im/v1/messages).

Env:
    FEISHU_APP_ID, FEISHU_APP_SECRET
    FEISHU_VERIFY_TOKEN          (optional, validates event 'token')
    FEISHU_BASE_URL              (default https://open.feishu.cn)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .router import dispatch

router = APIRouter(prefix="/feishu", tags=["bots"])

FEISHU_BASE_URL = os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn").rstrip("/")


def _tenant_token() -> str:
    resp = requests.post(
        f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
        json={
            "app_id": os.environ["FEISHU_APP_ID"],
            "app_secret": os.environ["FEISHU_APP_SECRET"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def _reply(chat_id: str, text: str) -> None:
    token = _tenant_token()
    requests.post(
        f"{FEISHU_BASE_URL}/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        timeout=15,
    )


@router.post("/event")
async def event(request: Request) -> JSONResponse:
    body: Dict[str, Any] = await request.json()

    # 1. URL verification handshake.
    if body.get("type") == "url_verification":
        return JSONResponse({"challenge": body.get("challenge", "")})

    # 2. Optional verification-token check.
    verify = os.environ.get("FEISHU_VERIFY_TOKEN")
    token = body.get("token") or body.get("header", {}).get("token")
    if verify and token and token != verify:
        return JSONResponse({"msg": "invalid token"}, status_code=403)

    # 3. Message receive event (v2 schema).
    event_data = body.get("event", {})
    message = event_data.get("message", {})
    if message.get("message_type") == "text":
        content = json.loads(message.get("content", "{}")).get("text", "")
        # Strip @-mentions like "@_user_1 ".
        cleaned = " ".join(w for w in content.split() if not w.startswith("@_")).strip()
        reply = dispatch(cleaned)
        chat_id = message.get("chat_id")
        if chat_id:
            _reply(chat_id, reply)

    return JSONResponse({"code": 0})
