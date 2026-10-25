"""协议处理器：握手鉴权、会话捕获与失效重置。

由 `Connecter` 逐帧调用，不经过事件队列：HELLO → 按有无
session_id 决定 RESUME 续传或 IDENTIFY 新建并返回应答；READY → 捕获
session_id（该帧同时是 op=0，仍会入队分发给用户的 READY handler）；
INVALID_SESSION → d=false 时清空会话，使重连走 IDENTIFY；每条帧的 s
在此更新，供心跳与 RESUME 取用。
"""

from tomllib import load

from loguru import logger

from .config import Config
from .model import (
    Intent,
    Opcode,
    OutgoingFrame,
    Payload,
    identify_frame,
    resume_frame,
)
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
        if not isinstance(enabled, bool):
            raise ValueError(
                f"intents 分组 {group} 的值应为 true/false，实际为 {enabled!r}"
            )
        if enabled:
            intents |= intent
    return intents


_KNOWN_INTENTS_MASK = sum(intent.value for intent in Intent)


def resolve_intents(config: Config) -> int:
    """掩码优先于 intents.toml：Config.intents（Bot 参数或 INTENTS 环境变量）
    已给则原样下发并校验未知位，未给才回落文件。"""
    if config.intents is None:
        return get_intents(config.intents_file)
    unknown = config.intents & ~_KNOWN_INTENTS_MASK
    if unknown:
        # 平台可能新增 SDK 尚未收录的分组，未知位只告警不拦截
        logger.warning(
            f"intents 掩码含未知位 {unknown:#x}（当前 Intent 枚举未收录），将原样下发"
        )
    return config.intents


class Protocol:
    """协议处理器：维护握手/会话状态，返回需要回送的出站帧。"""

    def __init__(self, config: Config, session: Session, token: AccessToken) -> None:
        self._config = config
        self._session = session
        self._token = token
        # intents 是启动期配置：提前解析并缓存，重连时不再重复读 TOML；
        # 非法配置在装配阶段直接暴露，而不是等首次 HELLO
        self._intents = resolve_intents(config)

    async def on_frame(self, payload: Payload) -> OutgoingFrame | None:
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

    async def _handshake(self) -> OutgoingFrame:
        access_token = await self._token.get_access_token()

        if self._session.session_id:
            logger.info("发送 RESUME 恢复会话")
            return resume_frame(
                access_token, self._session.session_id, self._session.seq
            )
        return identify_frame(access_token, self._intents)

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
