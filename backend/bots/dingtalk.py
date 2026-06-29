"""DingTalk adapter — Stream mode (no public IP required).

Uses the official `dingtalk-stream` SDK to hold an outbound WebSocket to
DingTalk, so it runs anywhere (including behind NAT / on Aliyun FC with an
outbound connection). Each inbound message is routed through bots.router.

Env:
    DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET

Run:
    python -m bots.dingtalk
"""

from __future__ import annotations

import os

from .router import dispatch


def build_client():
    # Lazy import so the module loads without the SDK present (e.g. in tests).
    import dingtalk_stream
    from dingtalk_stream import AckMessage, ChatbotHandler, ChatbotMessage

    client_id = os.environ["DINGTALK_CLIENT_ID"]
    client_secret = os.environ["DINGTALK_CLIENT_SECRET"]

    class Handler(ChatbotHandler):
        async def process(self, callback):  # type: ignore[override]
            message = ChatbotMessage.from_dict(callback.data)
            reply = dispatch(message.text.content.strip())
            self.reply_text(reply, message)
            return AckMessage.STATUS_OK, "OK"

    credential = dingtalk_stream.Credential(client_id, client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        dingtalk_stream.chatbot.ChatbotMessage.TOPIC, Handler()
    )
    return client


def main() -> None:
    build_client().start_forever()


if __name__ == "__main__":
    main()
