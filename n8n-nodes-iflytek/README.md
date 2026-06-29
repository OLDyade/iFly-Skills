# n8n-nodes-iflytek

[n8n](https://n8n.io) community nodes for iFLYTEK skills — translation, proofreading,
TTS, OCR, speech transcription, and multimodal image understanding. One node per skill,
all sharing a single **iFLYTEK API** credential.

> Discoverable in n8n via the `n8n-community-node-package` keyword.

## How it works

Each node shells out (via `child_process.spawn`) to the corresponding Python skill script,
which is bundled into this package under `skills/` at build time. The node maps your
**iFLYTEK API** credential onto the env vars each script expects.

**Requirement:** the host running n8n must have **Python 3** available (override the
interpreter with the `PYTHON_BIN` env var) and the skill dependencies installed:

```bash
pip install requests websocket-client urllib3
```

## Install

Community nodes → install `n8n-nodes-iflytek`. Or manually:

```bash
npm install n8n-nodes-iflytek
```

## Nodes

`Translate`, `Proofread`, `HyperTts`, `ImageUnderstanding`, `OcrInvoice`, `ImageOcr`,
`PdfOcr`, `Transcribe`, `VoicecloneSynth`, `VideoTranslate` — each generated from
[`core/skills.yaml`](../core/skills.yaml).

## Develop

```bash
npm install
npm run generate        # regenerate node classes from skills.yaml (needs python + pyyaml)
npm run build           # bundle skills, tsc, copy icons
npm link                # then `npm link n8n-nodes-iflytek` in ~/.n8n/custom
```

The node `.node.ts` files are auto-generated — edit `skills.yaml` and re-run
`npm run generate` rather than hand-editing them.

## Publish

`npm publish` (CI runs this on a `v*` tag via
[`.github/workflows/publish-n8n.yml`](../../.github/workflows/publish-n8n.yml) with the
`NPM_TOKEN` secret).
