"""qqbotsdk：QQ 官方机器人 SDK 入口。

用法：构造 `EventEmitter(EventQueue())` 注册 handler，交给 `main(ee)`
启动；连接方式由 .env 的 CONNECTER 决定（websocket / webhook）。
架构详情见 docs/ARCHITECTURE.md。
"""

import asyncio

from dotenv import load_dotenv
from loguru import logger

from .config import Config
from .connecter import Connecter
from .di import Inject as Inject
from .di import make_container
from .emitter import BaseProtocol as BaseProtocol
from .emitter import EventEmitter as EventEmitter
from .queue import EventQueue as EventQueue

load_dotenv()


async def run_loop(emitter: EventEmitter | None = None) -> None:
    """启动 SDK。可传入外部构造的 EventEmitter 以注册 handler；
    不传时由容器自建。"""
    container = make_container(emitter)
    try:
        emitter = await container.get(EventEmitter)
        emitter.use_container(container)
        emitter.register_protocol(await container.get(BaseProtocol))
        connecter = await container.get(Connecter)

        logger.info(f"qqbotsdk 启动，连接方式: {Config.load().connecter}")
        await asyncio.gather(emitter.dispatch(), connecter.run())
    finally:
        # 容器关闭时统一释放共享的 HTTP 会话等 APP 级资源
        await container.close()


def main(emitter: EventEmitter | None = None) -> None:
    try:
        asyncio.run(run_loop(emitter))
    except KeyboardInterrupt:
        logger.info("qqbotsdk 已退出")
