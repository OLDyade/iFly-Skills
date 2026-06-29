# iFly-Skills Backend (Coze plugins + IM bots)

One FastAPI service that wraps the skill scripts behind HTTP, shared by two
distribution channels:

- **Coze (扣子) plugins** (#44) — per-skill OpenAPI 3.0 schemas + a publisher.
- **IM bots** (#46) — DingTalk / Feishu / WeCom adapters routing chat commands.

## Run locally

```bash
pip install ./core
pip install -r backend/requirements.txt
export IFLYTEK_APP_ID=... IFLYTEK_API_KEY=... IFLYTEK_API_SECRET=...
cd backend
uvicorn app.main:app --reload --port 8000
# POST a skill:
curl -s localhost:8000/skills/translate -d '{"text":"你好","to":"en"}'
```

Every skill is mounted at `POST /skills/{tool_name}`; `GET /healthz` lists them.
Text skills return `{"ok":true,"output":"..."}`; media skills return
`{"ok":true,"artifact_url":"..."}`. Credentials may also be passed per request
via `X-IFLYTEK-APP-ID` / `X-IFLYTEK-API-KEY` / `X-IFLYTEK-API-SECRET` headers.

## Coze plugins (#44)

```bash
# 1. Generate one OpenAPI 3.0 doc per skill.
python -m app.openapi_export --server-url https://your-host --out openapi

# 2. Preview the Coze create payloads (no API calls).
python -m coze.publish --region cn --dry-run

# 3. Publish (global = com, China = cn).
export COZE_API_TOKEN=... COZE_WORKSPACE_ID=...
python -m coze.publish --region cn --workspace-id "$COZE_WORKSPACE_ID"
```

## IM bots (#46)

| Platform | Transport | Setup |
|----------|-----------|-------|
| DingTalk | Stream (outbound WS, no public IP) | `DINGTALK_CLIENT_ID/SECRET`, run `python -m bots.dingtalk` |
| Feishu   | Event subscription webhook | `FEISHU_APP_ID/SECRET`, point events at `POST /feishu/event` |
| WeCom    | Callback URL (encrypted) | `WECOM_TOKEN/AES_KEY/CORP_ID`, set callback to `/wecom` |

Chat commands (see `bots/router.py`): `/translate`, `/proofread`, `/tts`,
`/describe`, `/ocr`, `/help`. The Feishu and WeCom routers are mounted on the
same FastAPI app; DingTalk runs as a separate Stream process.

## Deploy to Aliyun FC

Build the image (`backend/Dockerfile`, context = repo root), push
to ACR, then `s deploy` with [`s.yaml`](./s.yaml). FC is recommended for China
latency; the Feishu/WeCom webhooks use the function's HTTP trigger URL, and
DingTalk needs no inbound URL at all.
