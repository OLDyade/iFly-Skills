"""FastAPI backend wrapping the iFly-Skills runner.

Serves two consumers from one app:
  * Coze plugins (#44) — per-skill OpenAPI 3.0 schemas under openapi/.
  * IM bots (#46)      — command router in app/../bots posts to these routes.
"""
