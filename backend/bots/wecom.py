"""WeCom (企业微信) adapter — callback URL with message encryption.

Implements the WeCom callback contract: a GET echo handshake and POST message
events, both protected by the documented msg_signature (SHA1) + AES-CBC
encryption scheme. Replies are returned as passive encrypted XML.

Env:
    WECOM_TOKEN, WECOM_AES_KEY (43-char EncodingAESKey), WECOM_CORP_ID

Mount the APIRouter at /wecom and register the URL in the WeCom admin console.
"""

from __future__ import annotations

import base64
import hashlib
import os
import struct
import xml.etree.ElementTree as ET
from typing import Optional

from fastapi import APIRouter, Request, Response

from .router import dispatch

router = APIRouter(prefix="/wecom", tags=["bots"])


def _token() -> str:
    return os.environ["WECOM_TOKEN"]


def _aes_key() -> bytes:
    return base64.b64decode(os.environ["WECOM_AES_KEY"] + "=")


def _corp_id() -> str:
    return os.environ.get("WECOM_CORP_ID", "")


def _signature(*parts: str) -> str:
    return hashlib.sha1("".join(sorted(parts)).encode()).hexdigest()


def _decrypt(encrypt_b64: str) -> str:
    from Crypto.Cipher import AES  # lazy import (pycryptodome)

    key = _aes_key()
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    plain = cipher.decrypt(base64.b64decode(encrypt_b64))
    plain = plain[: -plain[-1]]  # strip PKCS#7 padding
    msg_len = struct.unpack(">I", plain[16:20])[0]
    return plain[20 : 20 + msg_len].decode("utf-8")


def _encrypt(text: str) -> str:
    from Crypto.Cipher import AES

    key = _aes_key()
    random16 = os.urandom(16)
    msg = text.encode("utf-8")
    raw = random16 + struct.pack(">I", len(msg)) + msg + _corp_id().encode()
    pad = 32 - (len(raw) % 32)
    raw += bytes([pad]) * pad
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    return base64.b64encode(cipher.encrypt(raw)).decode()


def _reply_xml(encrypt: str, timestamp: str, nonce: str) -> str:
    signature = _signature(_token(), timestamp, nonce, encrypt)
    return (
        "<xml>"
        f"<Encrypt><![CDATA[{encrypt}]]></Encrypt>"
        f"<MsgSignature><![CDATA[{signature}]]></MsgSignature>"
        f"<TimeStamp>{timestamp}</TimeStamp>"
        f"<Nonce><![CDATA[{nonce}]]></Nonce>"
        "</xml>"
    )


@router.get("")
async def verify(
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str,
) -> Response:
    if _signature(_token(), timestamp, nonce, echostr) != msg_signature:
        return Response("invalid signature", status_code=403)
    return Response(_decrypt(echostr))


@router.post("")
async def callback(
    request: Request,
    msg_signature: str,
    timestamp: str,
    nonce: str,
) -> Response:
    body = (await request.body()).decode("utf-8")
    encrypt = ET.fromstring(body).findtext("Encrypt") or ""
    if _signature(_token(), timestamp, nonce, encrypt) != msg_signature:
        return Response("invalid signature", status_code=403)

    msg = ET.fromstring(_decrypt(encrypt))
    if (msg.findtext("MsgType") or "") != "text":
        return Response("")  # ignore non-text quietly

    content = (msg.findtext("Content") or "").strip()
    reply_text = dispatch(content)

    reply = (
        "<xml>"
        f"<ToUserName><![CDATA[{msg.findtext('FromUserName')}]]></ToUserName>"
        f"<FromUserName><![CDATA[{msg.findtext('ToUserName')}]]></FromUserName>"
        f"<CreateTime>{timestamp}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{reply_text}]]></Content>"
        "</xml>"
    )
    return Response(
        _reply_xml(_encrypt(reply), timestamp, nonce),
        media_type="application/xml",
    )
