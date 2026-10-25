"""重连循环：健康断开立刻重连（不记连接/断开），失败才退避并记断开。"""

import asyncio
from typing import Any

import pytest
from loguru import logger

from qqbotsdk.connecter import Connecter, RateLimitError, _Heartbeat
from qqbotsdk.model import Opcode

pytestmark = pytest.mark.asyncio


def _make(monkeypatch: pytest.MonkeyPatch, seq: list[Any]) -> Connecter:
    """构造 connecter，并把 _connect 换成按 seq 依次返回（float=存活秒数，
    Exception=连接失败）。seq 用尽后抛 IndexError 中止 run() 的无限循环。"""
    conn = Connecter.__new__(Connecter)
    remaining = list(seq)

    async def fake_connect() -> float:
        item = remaining.pop(0)  # 用尽则 IndexError 逃出 run()
        if isinstance(item, Exception):
            raise item
        return float(item)

    monkeypatch.setattr(conn, "_connect", fake_connect)
    return conn


async def _run_capture(
    monkeypatch: pytest.MonkeyPatch, seq: list[Any]
) -> tuple[list[float], list[str]]:
    """跑 run() 直到 seq 用尽，返回 (sleep 延迟序列, 日志消息列表)。"""
    sleeps: list[float] = []
    logs: list[str] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        await real_sleep(0)  # 让出控制权，避免紧循环

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    sink_id = logger.add(lambda m: logs.append(m.record["message"]), level="INFO")
    try:
        conn = _make(monkeypatch, seq)
        with pytest.raises(IndexError):
            await conn.run()
    finally:
        logger.remove(sink_id)
    return sleeps, logs


async def test_healthy_disconnect_reconnects_without_delay_or_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """健康连接（存活 >= 稳定阈值）断开后立刻重连：不 sleep、不记连接/断开。"""
    sleeps, logs = await _run_capture(monkeypatch, [3600.0, 3600.0])

    assert sleeps == []  # 两次都立刻重连
    assert not any("已连接" in m or "已断开" in m for m in logs)


async def test_failed_reconnect_backs_off_and_logs_disconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """连不上时记断开并按退避等待，退避逐次翻倍。"""
    sleeps, logs = await _run_capture(monkeypatch, [3600.0, TimeoutError(), 0.0, 0.0])

    # 健康断开 → 无 sleep；失败后依次 1s、2s、4s
    assert sleeps == [1, 2, 4]
    assert sum("已断开" in m for m in logs) == 3


async def test_rate_limit_backs_off_hard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gateway 限流：退避 60s，且不重复记断开。"""
    sleeps, logs = await _run_capture(monkeypatch, [RateLimitError(), 3600.0])

    assert sleeps == [60]
    assert any("频率限制" in m for m in logs)
    assert not any("已断开" in m for m in logs)


async def test_flapping_connection_does_not_reset_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """连接建立后立刻掉线（存活 < 阈值）视为抖动：退避持续拉长，不归零。"""
    sleeps, _ = await _run_capture(monkeypatch, [0.5, 0.5, 0.5])

    assert sleeps == [1, 2, 4]  # 每次都等得更久（若归零会是 1,1,1）


class _TimedOutWS:
    """receive 永远超时的假 ws，记录每次传入的 timeout。"""

    def __init__(self) -> None:
        self.timeouts: list[float] = []

    async def receive(self, timeout: float) -> None:
        self.timeouts.append(timeout)
        raise TimeoutError


async def test_wait_frame_uses_handshake_deadline_before_hello() -> None:
    """HELLO 未到时按固定握手期限等，不能拿 50 分钟寿命余量傻等。"""
    conn = Connecter.__new__(Connecter)
    ws = _TimedOutWS()

    with pytest.raises(TimeoutError):
        await conn._wait_frame(ws, interval=0.0, remaining=1000.0)  # type: ignore[arg-type]

    assert ws.timeouts == [conn._HANDSHAKE_TIMEOUT]


async def test_wait_frame_lifetime_deadline_wins_over_handshake() -> None:
    """寿命余量比握手期限更早到：返回 None 走主动收尾，不触发重连退避。"""
    conn = Connecter.__new__(Connecter)
    ws = _TimedOutWS()

    result = await conn._wait_frame(ws, interval=0.0, remaining=0.5)  # type: ignore[arg-type]

    assert result is None
    assert ws.timeouts == [0.5]


async def test_wait_frame_silence_deadline_still_raises() -> None:
    """HELLO 之后静默超期仍按心跳看门狗处理。"""
    conn = Connecter.__new__(Connecter)
    ws = _TimedOutWS()

    with pytest.raises(TimeoutError):
        await conn._wait_frame(ws, interval=10.0, remaining=1000.0)  # type: ignore[arg-type]

    assert ws.timeouts == [10.0 * conn._SILENCE_FACTOR]


async def test_heartbeat_rejects_invalid_interval() -> None:
    """HELLO 的 heartbeat_interval 非正数/非数字时按协议错误重连。"""
    fut = asyncio.get_running_loop().create_future()
    heartbeat = _Heartbeat(fut, 1.2)

    with pytest.raises(RuntimeError, match="heartbeat_interval"):
        heartbeat.observe({"op": Opcode.HELLO, "d": {"heartbeat_interval": 0}})
    with pytest.raises(RuntimeError, match="heartbeat_interval"):
        heartbeat.observe({"op": Opcode.HELLO, "d": {"heartbeat_interval": "41250"}})


async def test_heartbeat_accepts_valid_interval() -> None:
    fut = asyncio.get_running_loop().create_future()
    heartbeat = _Heartbeat(fut, 1.2)

    heartbeat.observe({"op": Opcode.HELLO, "d": {"heartbeat_interval": 300}})

    assert fut.result() == 0.3
