"""Webhook 接入的协议层：op=13 验证请求应答（签名 event_ts + plain_token）。

由 `WebhookConnecter` 在验签前就地调用；返回的应答体由连接器直接写回 HTTP
响应，不走 reply 队列。
"""

from typing import Any, cast, override

from .config import Config
from .crypto import sign_msg
from .model import Opcode, Payload, ValidationData
from .protocol import BaseProtocol


class WebhookProtocol(BaseProtocol):
    def __init__(self, config: Config) -> None:
        self._config = config

    @override
    async def on_frame(self, payload: Payload) -> dict[str, Any] | None:
        if payload.get("op") != Opcode.VALIDATION:
            return None
        d = payload.get("d")
        if not isinstance(d, dict):
            return None
        data = cast(ValidationData, d)
        return {
            "plain_token": data["plain_token"],
            "signature": sign_msg(
                self._config.app_secret,
                data["event_ts"] + data["plain_token"],
            ),
        }
