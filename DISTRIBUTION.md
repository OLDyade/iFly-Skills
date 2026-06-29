# iFly-Skills Distribution Channels

Channels that expose the skills in [`skills/`](skills/) to external ecosystems.
All four wrap the **same** skill scripts through one shared foundation, so a skill
defined once in [`core/skills.yaml`](core/skills.yaml) flows to every channel.

```
core/                 Shared registry, credential shim, runner, schema generators
mcp-server/           #43  MCP server (Smithery + Glama)
backend/              #44  Coze plugins  +  #46  IM bots (one FastAPI app)
n8n-nodes-iflytek/    #47  n8n community nodes
```

## Shared core ([`core/`](core/))

| Concern | Where | Notes |
|---------|-------|-------|
| Manifest | `skills.yaml` | One declarative entry per tool — the single source of truth. Each `entry.script` is repo-root-relative (e.g. `skills/iflytek-translate/scripts/translate.py`). |
| Credentials | `credentials.py` | Canonical `IFLYTEK_APP_ID/API_KEY/API_SECRET` → each script's `XFEI_*`/`XFYUN_*`/`IFLY_*` vars. **Skill scripts are never modified.** |
| Execution | `runner.py` | Builds argv, injects creds, runs the script, captures text/file/task output. |
| Schemas | `schema.py` | Manifest → JSON Schema (MCP `inputSchema`) **and** OpenAPI 3.0 (Coze), one code path. |
| Validation | `introspect.py` | CI check that the manifest matches the scripts' argparse. |

```bash
pip install ./core
python -m pytest core/tests
python -m iflyskills_core.introspect      # validate manifest vs scripts
```

## Channels

| Issue | Channel | Entry point | Publish |
|-------|---------|-------------|---------|
| [#43](https://github.com/iflytek/iFly-Skills/issues/43) | MCP server | `iflyskills-mcp` (stdio) | Smithery `smithery.yaml`, Glama `glama.json`, CI on `v*` |
| [#44](https://github.com/iflytek/iFly-Skills/issues/44) | Coze plugin | `POST /skills/{tool}` + `coze/publish.py` | `api.coze.com` / `api.coze.cn` |
| [#46](https://github.com/iflytek/iFly-Skills/issues/46) | IM bots | `bots/` (DingTalk/Feishu/WeCom) | Aliyun FC `s.yaml` |
| [#47](https://github.com/iflytek/iFly-Skills/issues/47) | n8n nodes | `n8n-nodes-iflytek` | npm on `v*` |

See each subdirectory's README for run + publish instructions.

## Credentials

Every channel takes **one** canonical credential set and maps it onto whatever env
var names each skill script expects — see [`CREDENTIALS.md`](CREDENTIALS.md) for how
to obtain the iFLYTEK App ID / API Key / API Secret and configure each channel.

```
IFLYTEK_APP_ID, IFLYTEK_API_KEY, IFLYTEK_API_SECRET
```

## What requires a maintainer

The code, config, CI workflows, and docs are publish-ready. Going live needs
accounts/secrets held by the maintainer: `SMITHERY_TOKEN`, `GLAMA_TOKEN`,
`NPM_TOKEN`, `COZE_API_TOKEN`, and Aliyun ACR/FC access. CI workflows are guarded
on each secret and no-op until configured.
