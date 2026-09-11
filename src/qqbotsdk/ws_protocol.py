"""WebSocket 接入的协议层：IDENTIFY/RESUME 鉴权、定时心跳、序列号跟踪。

识别 HELLO 后启动 apscheduler 心跳；断线重连时若已有 session_id
则发 RESUME 续传，收到不可恢复的 INVALID_SESSION 才清空会话重新 IDENTIFY。
"""

from tomllib import load
from typing import override

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from .config import Config
from .emitter import BaseProtocol, EventEmitter
from .model import (
    HelloData,
    IdentifyData,
    Intent,
    Opcode,
    Payload,
    ResumeData,
    payload_of,
)
from .payloads import Ready
from .queue import EventQueue
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
    def __init__(
        self,
        config: Config,
        queue: EventQueue,
        session: Session,
        token: AccessToken,
    ) -> None:
        self._config = config
        self._queue = queue
        self._session = session
        self._token = token
        self._scheduler = AsyncIOScheduler()
        self._heartbeat_job_id = "heartbeat"

    @override
    def register(self, emitter: EventEmitter) -> None:
        emitter.on(Opcode.HELLO)(self.identify)
        emitter.on(Opcode.HEARTBEAT)(self.heartbeat)
        emitter.on("READY")(self.ready)
        emitter.on(Opcode.INVALID_SESSION)(self.invalid_session)

    @override
    def on_payload(self, payload: Payload) -> None:
        seq = payload.get("s")
        if isinstance(seq, int):
            self._session.update_sequence(seq)

    async def identify(self, data: HelloData) -> Payload:
        if not self._scheduler.running:
            self._scheduler.add_job(
                self.send_heartbeat,
                "interval",
                seconds=data["heartbeat_interval"] / 1000,
                id=self._heartbeat_job_id,
            )
            self._scheduler.start()
            logger.info(f"心跳任务已启动，间隔 {data['heartbeat_interval']}ms")

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

    async def heartbeat(self, _) -> Payload:
        return payload_of(Opcode.HEARTBEAT, self._session.sequence_id)

    async def send_heartbeat(self) -> None:
        await self._queue.put_reply(await self.heartbeat(None))

    async def ready(self, ready: Ready) -> None:
        self._session.session_id = ready.session_id
        logger.info("会话已建立（READY）")

    async def invalid_session(self, resumable: bool) -> None:
        if not resumable:
            self._session.session_id = None
            logger.warning("会话已失效，下次连接将重新 IDENTIFY")
