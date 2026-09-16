"""Webhook 接入的协议层：op=13 验证请求应答（签名 event_ts + plain_token）。"""

from typing import override

from .config import Config
from .crypto import sign_msg
from .emitter import BaseProtocol, EventEmitter
from .model import Opcode, ValidationData
from .queue import EventQueue
from .session import Session


class WebhookProtocol(BaseProtocol):
    def __init__(self, config: Config, queue: EventQueue, session: Session) -> None:
        self._config = config

    @override
    def register(self, emitter: EventEmitter) -> None:
        emitter.on(Opcode.VALIDATION)(self.validation)

    async def validation(self, data: ValidationData) -> dict[str, str]:
        return {
            "plain_token": data["plain_token"],
            "signature": sign_msg(
                self._config.app_secret,
                data["event_ts"] + data["plain_token"],
            ),
        }
