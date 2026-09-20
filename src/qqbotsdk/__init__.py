"""qqbotsdk：QQ 官方机器人 SDK 入口。

用法：构造 `EventEmitter()` 注册 handler，交给 `main(ee)`
启动；连接方式由 .env 的 CONNECTER 决定（websocket / webhook）。
架构详情见 docs/ARCHITECTURE.md。
"""

import asyncio

from aiohttp import ClientSession
from dotenv import load_dotenv
from loguru import logger

from .api import BotApi
from .config import Config
from .connecter import Connecter as Connecter
from .connecter import WebhookConnecter, WebsocketConnecter
from .emitter import BaseProtocol as BaseProtocol
from .emitter import EventEmitter as EventEmitter
from .queue import EventQueue as EventQueue
from .session import Session
from .token import AccessToken
from .webhook_protocol import WebhookProtocol
from .ws_protocol import WebsocketProtocol

load_dotenv()


async def run_loop(emitter: EventEmitter | None = None) -> None:
    """启动 SDK。可传入外部构造的 EventEmitter 以注册 handler；不传时自建。

    全部组件在此显式装配，并按类型登记到 emitter.services 供 handler
    参数注入；共享的 HTTP 连接池随 run_loop 结束释放。
    """
    if emitter is None:
        emitter = EventEmitter()

    config = Config.load()
    http = ClientSession(timeout=config.timeout)
    session = Session()
    token = AccessToken(config, http)
    api = BotApi(config, http, token)
    emitter.services.update(
        {
            EventEmitter: emitter,
            EventQueue: emitter.queue,
            Config: config,
            Session: session,
            ClientSession: http,
            AccessToken: token,
            BotApi: api,
        }
    )

    match config.connecter:
        case "websocket":
            protocol = WebsocketProtocol(config, session, token)
            connecter = WebsocketConnecter(config, http, token, session, emitter.queue)
        case "webhook":
            protocol = WebhookProtocol(config)
            connecter = WebhookConnecter(config, emitter.queue, emitter.handle)
        case unknown:
            raise ValueError(f"未知的 CONNECTER: {unknown}")

    emitter.register_protocol(protocol)
    logger.info(f"qqbotsdk 启动，连接方式: {config.connecter}")
    try:
        await asyncio.gather(emitter.dispatch(), connecter.run())
    finally:
        # 在飞的后台 handler 先于连接池收尾，避免用到已关闭的 ClientSession
        await emitter.close()
        # 全 SDK 共享一个连接池，统一在此释放
        await http.close()


def main(emitter: EventEmitter | None = None) -> None:
    try:
        asyncio.run(run_loop(emitter))
    except KeyboardInterrupt:
        logger.info("qqbotsdk 已退出")
