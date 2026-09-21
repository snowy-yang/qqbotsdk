"""重连循环：健康断开立刻重连（不记连接/断开），失败才退避并记断开。"""

import asyncio
from typing import Any

import pytest
from loguru import logger

from qqbotsdk.connecter import RateLimitError, WebsocketConnecter

pytestmark = pytest.mark.asyncio


def _make(monkeypatch: pytest.MonkeyPatch, seq: list[Any]) -> WebsocketConnecter:
    """构造 connecter，并把 _connect 换成按 seq 依次返回（float=存活秒数，
    Exception=连接失败）。seq 用尽后抛 IndexError 中止 run() 的无限循环。"""
    conn = WebsocketConnecter.__new__(WebsocketConnecter)
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
