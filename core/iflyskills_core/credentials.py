"""Credential shim.

The skill scripts read iFLYTEK credentials from inconsistent environment
variable names (XFEI_*, XFYUN_*, IFLY_*) and one composite skill uses
LLM_API_KEY / OCR_API_KEY / TRANSLATE_API_KEY. Rather than modify the
published scripts, callers supply ONE canonical credential set and this module
maps it onto whatever names the target script expects, at call time.

Canonical inputs (read from the provided dict, falling back to os.environ):
    IFLYTEK_APP_ID
    IFLYTEK_API_KEY
    IFLYTEK_API_SECRET

Composite skills additionally accept the pre-split keys
(IFLYTEK_LLM_API_KEY, IFLYTEK_OCR_API_KEY, IFLYTEK_TRANSLATE_API_KEY); when
those are absent the generic IFLYTEK_API_KEY is reused for each.
"""

from __future__ import annotations

import os
from typing import Dict, Mapping, Optional

CANONICAL_APP_ID = "IFLYTEK_APP_ID"
CANONICAL_API_KEY = "IFLYTEK_API_KEY"
CANONICAL_API_SECRET = "IFLYTEK_API_SECRET"

# cred_profile -> env-var prefix used by that family of scripts.
_PREFIX_PROFILES = {
    "xfei": "XFEI",
    "xfyun": "XFYUN",
    "ifly": "IFLY",
}


class CredentialError(RuntimeError):
    """Raised when required canonical credentials are missing."""


def _lookup(canonical: str, overrides: Optional[Mapping[str, str]]) -> Optional[str]:
    if overrides and overrides.get(canonical):
        return overrides[canonical]
    return os.environ.get(canonical)


def resolve_env(
    cred_profile: str,
    overrides: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Build the subprocess env vars a skill needs from canonical credentials.

    `overrides` (e.g. per-request credentials from an API call) take precedence
    over the ambient process environment. Returns ONLY the credential vars to
    merge into the child environment; the runner overlays them on os.environ.
    """
    if cred_profile == "none":
        return {}

    app_id = _lookup(CANONICAL_APP_ID, overrides)
    api_key = _lookup(CANONICAL_API_KEY, overrides)
    api_secret = _lookup(CANONICAL_API_SECRET, overrides)

    if cred_profile in _PREFIX_PROFILES:
        missing = [
            name
            for name, val in (
                (CANONICAL_APP_ID, app_id),
                (CANONICAL_API_KEY, api_key),
                (CANONICAL_API_SECRET, api_secret),
            )
            if not val
        ]
        if missing:
            raise CredentialError(
                "Missing required credentials: " + ", ".join(missing)
            )
        prefix = _PREFIX_PROFILES[cred_profile]
        return {
            f"{prefix}_APP_ID": app_id,
            f"{prefix}_API_KEY": api_key,
            f"{prefix}_API_SECRET": api_secret,
        }

    if cred_profile == "composite":
        llm = _lookup("IFLYTEK_LLM_API_KEY", overrides) or api_key
        ocr = _lookup("IFLYTEK_OCR_API_KEY", overrides) or api_key
        translate = _lookup("IFLYTEK_TRANSLATE_API_KEY", overrides) or api_key
        if not (llm and ocr and translate):
            raise CredentialError(
                "Composite skill requires IFLYTEK_API_KEY or the per-service "
                "keys IFLYTEK_LLM_API_KEY / IFLYTEK_OCR_API_KEY / "
                "IFLYTEK_TRANSLATE_API_KEY"
            )
        return {
            "LLM_API_KEY": llm,
            "OCR_API_KEY": ocr,
            "TRANSLATE_API_KEY": translate,
        }

    raise CredentialError(f"Unknown cred_profile: {cred_profile}")
