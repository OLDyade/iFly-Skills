# iFLYTEK Credentials

Every skill calls an iFLYTEK (讯飞) open-platform capability, which requires three
credentials tied to your application: **App ID**, **API Key**, and **API Secret**.

## 1. Get the credentials

1. Sign in to the iFLYTEK open platform console: <https://console.xfyun.cn/>.
2. Create an application (创建应用), or open an existing one.
3. On the application page you'll find **APPID**, **APISecret**, and **APIKey**.
4. **Enable the specific ability** each skill uses (e.g. 语音合成 for TTS, 通用文字识别 for
   OCR, 机器翻译 for translation). A skill returns an authorization/quota error until its
   ability is enabled for that App ID. Each skill's `SKILL.md` names the ability it needs.

> One application's App ID/Key/Secret can serve multiple abilities — enable each ability
> you intend to use on the same application.

## 2. The canonical set

All distribution channels accept **one** canonical credential set:

| Variable | Value |
|----------|-------|
| `IFLYTEK_APP_ID` | the application's APPID |
| `IFLYTEK_API_KEY` | the application's APIKey |
| `IFLYTEK_API_SECRET` | the application's APISecret |

The shared core (`core/credentials.py`) maps these onto whatever variable names each
skill script historically expects, so **the skill scripts are never modified**:

| Skill family | Script env vars (set for you) |
|--------------|-------------------------------|
| hyper-tts, speed-transcription | `XFEI_APP_ID` / `XFEI_API_KEY` / `XFEI_API_SECRET` |
| ocr-invoice, translate, video-translate | `XFYUN_APP_ID` / `XFYUN_API_KEY` / `XFYUN_API_SECRET` |
| image-understanding, pdf-image-ocr, text-proofread, voiceclone-tts | `IFLY_APP_ID` / `IFLY_API_KEY` / `IFLY_API_SECRET` |
| contract-intelligence-review (composite) | `LLM_API_KEY` / `OCR_API_KEY` / `TRANSLATE_API_KEY` — derived from `IFLYTEK_API_KEY`, or set per-service with `IFLYTEK_LLM_API_KEY` / `IFLYTEK_OCR_API_KEY` / `IFLYTEK_TRANSLATE_API_KEY` |

You only ever supply the canonical three (plus the optional composite overrides).

## 3. Configure per channel

| Channel | How to provide credentials |
|---------|----------------------------|
| **MCP server** | Set `IFLYTEK_APP_ID/API_KEY/API_SECRET` in the server env. Smithery/Glama collect them via the config schema in `mcp-server/smithery.yaml` / `glama.json`. |
| **Backend (Coze + IM bots)** | Set the three env vars on the service, **or** pass them per request via the `X-IFLYTEK-APP-ID` / `X-IFLYTEK-API-KEY` / `X-IFLYTEK-API-SECRET` headers. |
| **n8n nodes** | Create an **iFLYTEK API** credential (App ID / API Key / API Secret) and attach it to any node. |
| **Coze plugin** | The backend holds the credentials; the published plugin calls the backend. |

## 4. Security notes

- Treat the API Secret like a password — never commit it. `.env*`, `*.pem`, `*.key` are
  gitignored. CI publish workflows read tokens from repository **secrets**, never the repo.
- Rotate the API Secret from the console if it is ever exposed.
