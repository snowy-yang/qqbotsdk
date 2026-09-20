"""WebSocket 接入的协议层：IDENTIFY/RESUME 鉴权、序列号跟踪与会话保持。

心跳与连接生命周期归 WebsocketConnecter；本层只负责会话语义——
识别 HELLO 后按有无 session_id 决定 RESUME 续传或 IDENTIFY 新建，
收到不可恢复的 INVALID_SESSION（d=false）才清空会话重新 IDENTIFY。
"""

from tomllib import load
from typing import override

from loguru import logger

from .config import Config
from .emitter import BaseProtocol, EventEmitter
from .model import (
    IdentifyData,
    Intent,
    Opcode,
    Payload,
    ResumeData,
    payload_of,
)
from .payloads import Ready
from .session import Session
from .token import AccessToken

# TOML 分组名即 Intent 枚举成员名
INTENT_GROUPS: dict[str, Intent] = {name: Intent[name] for name in Intent.__members__}


def get_intents(path: str) -> int:
    try:
        with open(path, "rb") as f:
            config = load(f)
    except FileNotFoundError:
        logger.warning(f"未找到 {path}，默认不监听任何事件")
        return 0

    intents = 0
    for group, events in config.items():
        if intent := INTENT_GROUPS.get(group):
            if isinstance(events, dict) and any(events.values()):
                intents |= intent
        else:
            logger.warning(f"未知的 intents 分组: {group}")
    return intents


class WebsocketProtocol(BaseProtocol):
    def __init__(self, config: Config, session: Session, token: AccessToken) -> None:
        self._config = config
        self._session = session
        self._token = token

    @override
    def register(self, emitter: EventEmitter) -> None:
        emitter.on(Opcode.HELLO)(self.identify)
        emitter.on("READY")(self.ready)
        emitter.on(Opcode.INVALID_SESSION)(self.invalid_session)

    @override
    def on_payload(self, payload: Payload) -> None:
        seq = payload.get("s")
        if isinstance(seq, int):
            self._session.update_sequence(seq)

    async def identify(self) -> Payload:
        access_token = await self._token.get_access_token()

        d: ResumeData | IdentifyData
        if self._session.session_id:
            op = Opcode.RESUME
            d = {
                "token": f"QQBot {access_token}",
                "session_id": self._session.session_id,
                "seq": self._session.seq,
            }
            logger.info("发送 RESUME 恢复会话")
        else:
            op = Opcode.IDENTIFY
            d = {
                "token": f"QQBot {access_token}",
                "intents": get_intents(self._config.intents_file),
                "shard": (0, 1),
                "properties": {},
            }

        return payload_of(op, d)

    async def ready(self, ready: Ready) -> None:
        self._session.session_id = ready.session_id
        logger.info("会话已建立（READY）")

    async def invalid_session(self, resumable: bool) -> None:
        if not resumable:
            self._session.session_id = None
            logger.warning("会话已失效，下次连接将重新 IDENTIFY")
