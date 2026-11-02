"""底层网关示例: 不用上层框架, 自己消费原始帧.

配置好 .env 后运行::

    python examples/raw_websocket.py
"""

import asyncio

from loguru import logger

from qqbotsdk.api.core import session
from qqbotsdk.errors import QQBotGatewayError
from qqbotsdk.model.event import parse_event
from qqbotsdk.ws import DEFAULT_INTENTS, WILDCARD_EVENT, GatewayPayload, QQBotWebSocket


async def on_any(payload: GatewayPayload) -> None:
    """回调方式: 每次收到 Dispatch 就执行, 不阻塞收包."""
    event = parse_event(payload)
    if event is None:
        logger.debug(f"未建模事件 {payload.t}")
        return
    logger.info(f"回调收到 {payload.t}: {type(event).__name__}")


async def main() -> None:
    async with QQBotWebSocket(intents=DEFAULT_INTENTS) as ws:
        ws.on(WILDCARD_EVENT, on_any)  # 通配注册

        await ws.wait_ready(timeout=30)
        logger.info(f"已连接, session_id={ws.session_id} seq={ws.seq}")

        # 同时保留拉取式消费: 两者拿到的是同一个 payload 对象
        async for payload in ws:
            if payload.t == "READY":
                logger.info("READY 也走 async for")
                continue

            event = parse_event(payload)
            logger.info(f"async for 收到 {payload.t} -> {type(event).__name__}")

        if isinstance(ws.last_error, QQBotGatewayError):
            logger.error(f"网关终止: code={ws.last_error.code} {ws.last_error.reason}")

    await session.close()


if __name__ == "__main__":
    asyncio.run(main())
