# iFly-Skills MCP Server

Exposes every skill in this repository as a [Model Context Protocol](https://modelcontextprotocol.io)
tool. Tools and their JSON Schemas are generated from
[`core/skills.yaml`](../core/skills.yaml) — adding a skill there exposes it here
automatically.

## Tools

One tool per skill, e.g. `translate`, `proofread`, `hyper_tts`, `image_understanding`,
`ocr_invoice`, `image_ocr`, `pdf_ocr`, `transcribe`, `voiceclone_synth`, `video_translate`.
Run the server and call `tools/list` for the live, schema-complete list.

## Credentials

Set the canonical iFLYTEK credentials in the environment; the server maps them onto each
skill's expected variables internally:

```
IFLYTEK_APP_ID, IFLYTEK_API_KEY, IFLYTEK_API_SECRET
```

## Run locally (stdio)

```bash
pip install ./core ./mcp-server
pip install -r mcp-server/requirements-skills.txt
export IFLYTEK_APP_ID=... IFLYTEK_API_KEY=... IFLYTEK_API_SECRET=...
iflyskills-mcp           # speaks MCP over stdio
```

Add to a client (Claude Desktop / Cursor / etc.):

```json
{
  "mcpServers": {
    "iflyskills": {
      "command": "iflyskills-mcp",
      "env": {
        "IFLYTEK_APP_ID": "...",
        "IFLYTEK_API_KEY": "...",
        "IFLYTEK_API_SECRET": "..."
      }
    }
  }
}
```

## Docker

The image bundles the skill scripts so tools execute end-to-end. Build from the repo root:

```bash
docker build -f mcp-server/Dockerfile -t iflyskills-mcp .
docker run -i --rm -e IFLYTEK_APP_ID -e IFLYTEK_API_KEY -e IFLYTEK_API_SECRET iflyskills-mcp
```

## Publishing

- **Smithery** — [`smithery.yaml`](./smithery.yaml) declares an stdio runtime and the credential
  config schema. Connect the repo at [smithery.ai](https://smithery.ai) or let CI publish on a
  `v*` tag (requires the `SMITHERY_TOKEN` secret).
- **Glama** — [`glama.json`](./glama.json) carries the listing metadata; Glama indexes it
  automatically once the repo is public, and CI can ping its API on release.
- **Stretch:** submit a PR adding this server to
  [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers).

See [`.github/workflows/publish-mcp.yml`](../../.github/workflows/publish-mcp.yml).
