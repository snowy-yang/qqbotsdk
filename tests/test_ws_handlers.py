"""事件回调注册 (on/off) 的测试: 全部打本地假网关, 不访问真实域名.

覆盖: 精确事件名与 ``"*"`` 通配、多个回调按注册顺序、回调异常隔离、
回调与 ``async for`` 并存、``off()`` 生效、``close()`` 取消未完成的回调任务.
"""

import asyncio
import json
from typing import Any

import pytest
from aiohttp import WSMsgType, web

from qqbotsdk.api import core
from qqbotsdk.ws import QQBotWebSocket
from qqbotsdk.ws import client as client_mod
from qqbotsdk.ws.payload import GatewayPayload

# 假网关在 READY 之后下发的 4 条 Dispatch
DISPATCHES: list[dict[str, Any]] = [
    {"t": "GROUP_AT_MESSAGE_CREATE", "id": "evt-1", "d": {"id": "m1"}},
    {"t": "GROUP_AT_MESSAGE_CREATE", "id": "evt-2", "d": {"id": "m2"}},
    {"t": "GROUP_AT_MESSAGE_CREATE", "id": "evt-3", "d": {"id": "m3"}},
    {"t": "C2C_MESSAGE_CREATE", "id": "evt-4", "d": {"id": "m4"}},
]

# READY + 4 条 Dispatch
TOTAL_EVENTS = len(DISPATCHES) + 1


async def _receive_json(
    ws: web.WebSocketResponse,
    timeout: float = 5.0,
) -> dict[str, Any]:
    msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
    assert msg.type is WSMsgType.TEXT
    payload: dict[str, Any] = json.loads(msg.data)
    return payload


async def _fake_token(*, force: bool = False) -> str:
    """替换真实的凭证获取, 保证测试不会发出取 token 的请求."""
    return "test-token"


class FakeGateway:
    """本地假网关: Hello -> Identify -> READY -> 若干 Dispatch -> 关闭."""

    def __init__(
        self,
        dispatches: list[dict[str, Any]],
        *,
        hold_seconds: float | None = 0.05,
    ) -> None:
        """hold_seconds 为 None 时一直等到客户端关闭, 否则保持指定秒数后关闭."""
        self._dispatches = dispatches
        self._hold = hold_seconds
        self._runner: web.AppRunner | None = None
        self.ws_url = ""
        self.connections = 0
        self.payloads: list[dict[str, Any]] = []

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/websocket", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        host, port = self._runner.addresses[0]
        self.ws_url = f"ws://{host}:{port}/websocket"

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.connections += 1
        # 心跳间隔取大值, 让测试期间不触发心跳
        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 45000}})
        self.payloads.append(await _receive_json(ws))
        await ws.send_json(
            {"op": 0, "s": 1, "t": "READY", "d": {"session_id": "sess-1"}}
        )
        for seq, event in enumerate(self._dispatches, start=2):
            await ws.send_json(
                {
                    "op": 0,
                    "s": seq,
                    "t": event["t"],
                    "id": event["id"],
                    "d": event["d"],
                }
            )
        if self._hold is None:
            # 一直等到客户端主动关闭
            await _wait_close(ws)
        else:
            await asyncio.sleep(self._hold)
        await ws.close()
        return ws


async def _wait_close(ws: web.WebSocketResponse) -> None:
    """等客户端主动关闭连接."""
    while True:
        msg = await ws.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            return
        if msg.type is WSMsgType.ERROR:
            return


async def test_exact_and_wildcard_handlers_coexist_with_async_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(DISPATCHES)
    await gateway.start()
    await core.session.close()
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)

    exact: list[GatewayPayload] = []
    wildcard: list[GatewayPayload] = []
    all_done = asyncio.Event()

    async def on_group(payload: GatewayPayload) -> None:
        exact.append(payload)

    async def on_any(payload: GatewayPayload) -> None:
        wildcard.append(payload)
        if len(wildcard) == TOTAL_EVENTS:
            all_done.set()

    events: list[str] = []
    try:
        async with QQBotWebSocket(url=gateway.ws_url, auto_reconnect=False) as ws:
            ws.on("GROUP_AT_MESSAGE_CREATE", on_group)
            ws.on("*", on_any)
            for _ in range(TOTAL_EVENTS):
                payload = await asyncio.wait_for(anext(ws), timeout=5)
                events.append(payload.t or "")
            # 回调是独立任务, 等它们跑完再做断言
            await asyncio.wait_for(all_done.wait(), timeout=5)
    finally:
        await core.session.close()
        await gateway.stop()

    # async for 仍然收到全部事件, 与回调并存
    assert events == [
        "READY",
        "GROUP_AT_MESSAGE_CREATE",
        "GROUP_AT_MESSAGE_CREATE",
        "GROUP_AT_MESSAGE_CREATE",
        "C2C_MESSAGE_CREATE",
    ]
    # 精确事件名只收到 3 条群消息
    assert len(exact) == 3
    assert all(isinstance(item, GatewayPayload) for item in exact)
    assert all(item.t == "GROUP_AT_MESSAGE_CREATE" for item in exact)
    assert exact[0].d == {"id": "m1"}
    # 通配收到全部 Dispatch, 含 READY / C2C
    assert [item.t for item in wildcard] == events
    # 回调与 async for 拿到的是同一个数据包对象
    assert wildcard[1] is exact[0]


async def test_handler_exception_does_not_break_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(DISPATCHES)
    await gateway.start()
    await core.session.close()
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)

    boom_calls = 0
    received: list[str] = []
    recorder_done = asyncio.Event()

    async def boom(_payload: GatewayPayload) -> None:
        nonlocal boom_calls
        boom_calls += 1
        raise RuntimeError("回调故意抛出的异常")

    async def recorder(payload: GatewayPayload) -> None:
        received.append(payload.t or "")
        if len(received) == TOTAL_EVENTS:
            recorder_done.set()

    try:
        async with QQBotWebSocket(url=gateway.ws_url, auto_reconnect=False) as ws:
            ws.on("*", boom)
            ws.on("*", recorder)
            for _ in range(TOTAL_EVENTS):
                await asyncio.wait_for(anext(ws), timeout=5)
            await asyncio.wait_for(recorder_done.wait(), timeout=5)
    finally:
        await core.session.close()
        await gateway.stop()

    # 每个事件都触发了会抛异常的回调, 但没有影响连接
    assert boom_calls == TOTAL_EVENTS
    # 同一个事件后面的回调照常执行
    assert received == [
        "READY",
        "GROUP_AT_MESSAGE_CREATE",
        "GROUP_AT_MESSAGE_CREATE",
        "GROUP_AT_MESSAGE_CREATE",
        "C2C_MESSAGE_CREATE",
    ]
    assert gateway.connections == 1


async def test_off_stops_callbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = FakeGateway(DISPATCHES)
    await gateway.start()
    await core.session.close()
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)

    calls: list[str] = []
    kept_done = asyncio.Event()

    async def removed(payload: GatewayPayload) -> None:
        calls.append("removed")

    async def kept(payload: GatewayPayload) -> None:
        calls.append("kept")
        if calls.count("kept") == 3:
            kept_done.set()

    async def wildcard(payload: GatewayPayload) -> None:
        calls.append("wildcard")

    try:
        async with QQBotWebSocket(url=gateway.ws_url, auto_reconnect=False) as ws:
            ws.on("GROUP_AT_MESSAGE_CREATE", removed)
            ws.on("GROUP_AT_MESSAGE_CREATE", kept)
            ws.on("*", wildcard)
            # 只移除 removed, 清空通配
            ws.off("GROUP_AT_MESSAGE_CREATE", removed)
            ws.off("*")
            for _ in range(TOTAL_EVENTS):
                await asyncio.wait_for(anext(ws), timeout=5)
            await asyncio.wait_for(kept_done.wait(), timeout=5)
    finally:
        await core.session.close()
        await gateway.stop()

    assert "removed" not in calls
    assert calls.count("wildcard") == 0
    assert calls.count("kept") == 3


async def test_close_cancels_pending_handler_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 只发 READY, 然后保持连接, 让回调一直挂着
    gateway = FakeGateway([], hold_seconds=None)
    await gateway.start()
    await core.session.close()
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)

    started = asyncio.Event()
    cancelled: list[str] = []

    async def hanging(payload: GatewayPayload) -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append("cancelled")

    ws = QQBotWebSocket(url=gateway.ws_url, auto_reconnect=False)
    try:
        async with ws:
            ws.on("*", hanging)
            await asyncio.wait_for(anext(ws), timeout=5)
            await asyncio.wait_for(started.wait(), timeout=5)
            # 此时回调任务还在挂起
            assert ws._handler_tasks
        # close() 之后不应残留回调任务
        leftover = [
            task
            for task in asyncio.all_tasks()
            if getattr(task.get_coro(), "__qualname__", "").endswith("_run_handler")
        ]
    finally:
        await core.session.close()
        await gateway.stop()

    assert cancelled == ["cancelled"]
    assert not ws._handler_tasks
    assert leftover == []
