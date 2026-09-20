"""WebSocket 接入的协议层：握手鉴权、会话捕获与失效重置。

由 `WebsocketConnecter` 逐帧调用，不经过事件队列：HELLO → 按有无
session_id 决定 RESUME 续传或 IDENTIFY 新建并返回应答；READY → 捕获
session_id（该帧同时是 op=0，仍会入队分发给用户的 READY handler）；
INVALID_SESSION → d=false 时清空会话，使重连走 IDENTIFY；每条帧的 s
在此更新，供心跳与 RESUME 取用。
"""

from tomllib import load
from typing import override

from loguru import logger

from .config import Config
from .model import IdentifyData, Intent, Opcode, Payload, ResumeData, payload_of
from .protocol import BaseProtocol
from .session import Session
from .token import AccessToken

# TOML 分组名即 Intent 枚举成员名
INTENT_GROUPS: dict[str, Intent] = {name: Intent[name] for name in Intent.__members__}


def get_intents(path: str) -> int:
    """按 Intents 大类（分组）读取订阅掩码：分组为 true 即 OR 该位。

    配置只接受 `分组名 = true/false`。网关只认分组位掩码，组内事件无法
    单独订阅，因此旧版"`[分组]` 表内逐事件开关"的写法、拼错的分组名与
    非布尔值一律抛 ValueError——静默少订阅比启动即报错更难排查。
    """
    try:
        with open(path, "rb") as f:
            config = load(f)
    except FileNotFoundError:
        logger.warning(f"未找到 {path}，默认不监听任何事件")
        return 0

    intents = 0
    for group, enabled in config.items():
        intent = INTENT_GROUPS.get(group)
        if intent is None:
            raise ValueError(f"未知的 intents 分组: {group}")
        if isinstance(enabled, dict):
            raise ValueError(
                f"intents 分组 {group} 不支持组内事件开关，请改为 {group} = true/false"
            )
        if not isinstance(enabled, bool):
            raise ValueError(
                f"intents 分组 {group} 的值应为 true/false，实际为 {enabled!r}"
            )
        if enabled:
            intents |= intent
    return intents


class WebsocketProtocol(BaseProtocol):
    def __init__(self, config: Config, session: Session, token: AccessToken) -> None:
        self._config = config
        self._session = session
        self._token = token

    @override
    async def on_frame(self, payload: Payload) -> Payload | None:
        seq = payload.get("s")
        if isinstance(seq, int):
            self._session.update_sequence(seq)

        op = payload.get("op")
        if op == Opcode.HELLO:
            return await self._handshake()
        if op == Opcode.INVALID_SESSION:
            self._invalid_session(payload.get("d"))
        elif op == Opcode.DISPATCH and payload.get("t") == "READY":
            self._ready(payload.get("d"))
        return None

    async def _handshake(self) -> Payload:
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

    def _ready(self, d: object) -> None:
        if isinstance(d, dict):
            session_id = d.get("session_id")
            if isinstance(session_id, str):
                self._session.session_id = session_id
                logger.info("会话已建立（READY）")

    def _invalid_session(self, d: object) -> None:
        # 官方语义：d 为布尔，true=可 RESUME 续传
        if not d:
            self._session.session_id = None
            logger.warning("会话已失效，下次连接将重新 IDENTIFY")
