"""协议帧处理测试：协议处理器（WebsocketProtocol）就近处理握手续传语义，
不进事件分发；只有业务事件（op=0）由 emitter 分发给用户 handler。"""

import pytest

from qqbotsdk.config import Config
from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode
from qqbotsdk.session import Session
from qqbotsdk.ws_protocol import WebsocketProtocol


class FakeToken:
    """手搓 token 源，避免构造真实 AccessToken 去发网络请求。"""

    async def get_access_token(self) -> str:
        return "tok"


def make_protocol(session: Session | None = None) -> tuple[WebsocketProtocol, Session]:
    session = session or Session()
    config = Config(
        app_id="app",
        app_secret="secret",
        base_url="https://api.bot.qq.com",
        timeout=None,  # type: ignore[arg-type]
        connecter="websocket",
        intents_file="no-such.toml",
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/x",
    )
    return WebsocketProtocol(config, session, FakeToken()), session  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_hello_without_session_identifies():
    protocol, _ = make_protocol()
    reply = await protocol.on_frame(
        {"op": Opcode.HELLO, "d": {"heartbeat_interval": 1}}
    )
    assert reply is not None
    assert reply["op"] == Opcode.IDENTIFY
    assert reply["d"]["token"] == "QQBot tok"
    assert reply["d"]["shard"] == (0, 1)


@pytest.mark.asyncio
async def test_hello_with_session_resumes():
    protocol, session = make_protocol()
    session.session_id = "S1"
    session.update_sequence(7)
    reply = await protocol.on_frame({"op": Opcode.HELLO, "d": {}})
    assert reply is not None
    assert reply["op"] == Opcode.RESUME
    assert reply["d"]["session_id"] == "S1"
    assert reply["d"]["seq"] == 7


@pytest.mark.asyncio
async def test_ready_captures_session_without_reply():
    protocol, session = make_protocol()
    reply = await protocol.on_frame(
        {"op": Opcode.DISPATCH, "t": "READY", "d": {"session_id": "S9"}}
    )
    assert reply is None
    assert session.session_id == "S9"


@pytest.mark.asyncio
async def test_sequence_is_tracked_from_frames():
    protocol, session = make_protocol()
    await protocol.on_frame({"op": Opcode.DISPATCH, "t": "X", "s": 5, "d": {}})
    await protocol.on_frame(
        {"op": Opcode.DISPATCH, "t": "X", "s": 3, "d": {}}
    )  # 回退被忽略
    assert session.seq == 5


@pytest.mark.asyncio
async def test_invalid_session_resets_only_when_not_resumable():
    protocol, session = make_protocol()
    session.session_id = "S1"
    await protocol.on_frame({"op": Opcode.INVALID_SESSION, "d": True})
    assert session.session_id == "S1"  # 可续传，会话保留
    await protocol.on_frame({"op": Opcode.INVALID_SESSION, "d": False})
    assert session.session_id is None  # 不可续传，下次重连走 IDENTIFY


@pytest.mark.asyncio
async def test_business_event_returns_no_reply():
    """业务事件（op=0 非 READY）协议层不产生应答，只留给 emitter 分发。"""
    protocol, _ = make_protocol()
    reply = await protocol.on_frame(
        {"op": Opcode.DISPATCH, "t": "GROUP_AT_MESSAGE_CREATE", "d": {"content": "hi"}}
    )
    assert reply is None


@pytest.mark.asyncio
async def test_emit_drops_protocol_frames():
    """协议帧不进分发队列；万一进来也不得触达业务 handler。"""
    emitter = EventEmitter()
    called: list[str] = []

    @emitter.on(Opcode.HELLO)
    async def on_hello(_):
        called.append("hello")

    await emitter.emit({"op": Opcode.HELLO, "d": {"heartbeat_interval": 1}})
    assert called == []


@pytest.mark.asyncio
async def test_emit_drops_dispatch_without_t():
    emitter = EventEmitter()

    @emitter.on("READY")
    async def on_ready(_):
        raise AssertionError("不应被调用")

    await emitter.emit({"op": Opcode.DISPATCH, "d": {}})


@pytest.mark.asyncio
async def test_emit_ignores_missing_op():
    emitter = EventEmitter()
    await emitter.emit({"d": {}})  # 无 op，静默跳过
