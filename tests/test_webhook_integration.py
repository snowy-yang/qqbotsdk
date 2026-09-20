"""Webhook 接入的端到端集成测试：真实起 WebhookConnecter 的 http server，
覆盖 op=13 验证应答、合法签名放行、坏签名 401、按 id 去重。"""

import asyncio
import json
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer
from cryptography.hazmat.primitives.asymmetric import ed25519

from qqbotsdk.config import Config
from qqbotsdk.connecter import WebhookConnecter
from qqbotsdk.crypto import build_seed
from qqbotsdk.emitter import EventEmitter
from qqbotsdk.payloads import GroupAtMessage
from qqbotsdk.webhook_protocol import WebhookProtocol

SECRET = "webhook-test-secret"


def make_config(port: int) -> Config:
    return Config(
        app_id="app",
        app_secret=SECRET,
        base_url="https://api.bot.qq.com",
        timeout=None,  # type: ignore[arg-type]
        connecter="webhook",
        intents_file="no-such-intents.toml",
        webhook_host="127.0.0.1",
        webhook_port=port,
        webhook_path="/qqbot/webhook",
    )


def sign(secret: str, timestamp: str, body: bytes) -> str:
    key = ed25519.Ed25519PrivateKey.from_private_bytes(build_seed(secret))
    return key.sign(timestamp.encode() + body).hex()


def event_body(event_id: str, content: str) -> dict[str, Any]:
    return {
        "op": 0,
        "id": event_id,
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {"content": content, "group_openid": "G1"},
    }


@pytest.mark.asyncio
async def test_webhook_end_to_end():
    config = make_config(0)
    emitter = EventEmitter()
    emitter.register_protocol(WebhookProtocol(config))
    connecter = WebhookConnecter(config, emitter.queue, emitter.handle)

    received: list[GroupAtMessage] = []

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def on_msg(msg: GroupAtMessage) -> None:
        received.append(msg)

    dispatch_task = asyncio.create_task(emitter.dispatch())
    server = TestServer(connecter._make_app())
    client = TestClient(server)
    await client.start_server()
    try:
        # 1. op=13 验证请求（不走验签），应答 plain_token + 对 event_ts+plain_token 的签名
        resp = await client.post(
            "/qqbot/webhook",
            json={"op": 13, "d": {"plain_token": "pt", "event_ts": "1726000000"}},
        )
        assert resp.status == 200
        ret = await resp.json()
        assert ret["plain_token"] == "pt"
        assert sign(SECRET, "1726000000", b"pt") == ret["signature"]

        # 2. 合法签名的事件推送 → 放行 → handler 收到 dataclass
        body = json.dumps(event_body("evt-1", "hello")).encode()
        resp = await client.post(
            "/qqbot/webhook",
            data=body,
            headers={
                "X-Signature-Timestamp": "1726000001",
                "X-Signature-Ed25519": sign(SECRET, "1726000001", body),
            },
        )
        assert resp.status == 200
        assert await resp.json() == {"opcode": 12}
        for _ in range(50):
            if received:
                break
            await asyncio.sleep(0.02)
        assert len(received) == 1
        assert received[0].content == "hello"

        # 3. 坏签名 → 401，事件不入队
        resp = await client.post(
            "/qqbot/webhook",
            data=body,
            headers={
                "X-Signature-Timestamp": "1726000002",
                "X-Signature-Ed25519": "00" * 64,
            },
        )
        assert resp.status == 401

        # 4. 同 id 重复推送 → 去重跳过，handler 不再收到
        resp = await client.post(
            "/qqbot/webhook",
            data=body,
            headers={
                "X-Signature-Timestamp": "1726000001",
                "X-Signature-Ed25519": sign(SECRET, "1726000001", body),
            },
        )
        assert resp.status == 200
        await asyncio.sleep(0.1)
        assert len(received) == 1
    finally:
        await client.close()
        dispatch_task.cancel()
        await asyncio.gather(dispatch_task, return_exceptions=True)
