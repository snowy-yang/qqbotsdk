"""Bot 门面：组件装配收进门面，用户侧只接触实例本身。

`Bot()` 构造即读 .env 校验配置；`@bot.on` 注册 handler（转发
EventEmitter，语义不变）；`run()` 同步启动，`start()` 供嵌入外部
asyncio 应用。连接池/token/API/services 登记与连接器选型全部内聚在
start() 的装配里，handler 经形参标注拿所需组件（含 Bot 自身）。
"""

import asyncio
from collections.abc import Callable
from typing import Any, overload

from aiohttp import ClientSession
from loguru import logger

from .api import BotApi
from .config import Config
from .connecter import Connecter, WebhookConnecter, WebsocketConnecter
from .emitter import EventEmitter, Handler
from .model import Opcode
from .queue import EventQueue
from .session import Session
from .token import AccessToken
from .webhook_protocol import WebhookProtocol
from .ws_protocol import WebsocketProtocol


class Bot:
    def __init__(self, config: Config | None = None) -> None:
        self._config = config if config is not None else Config.load()
        self._emitter = EventEmitter()
        self._http: ClientSession | None = None
        self._api: BotApi | None = None

    @property
    def config(self) -> Config:
        return self._config

    @property
    def services(self) -> dict[type, Any]:
        """组件登记表：自定义服务在此登记后即可按形参标注注入 handler。"""
        return self._emitter.services

    @property
    def queue(self) -> EventQueue:
        return self._emitter.queue

    @property
    def api(self) -> BotApi:
        """类型化 REST 门面；启动（run/start）后才存在。"""
        if self._api is None:
            raise RuntimeError("Bot 尚未启动，api/call_api 仅在 run()/start() 之后可用")
        return self._api

    @overload
    def on(
        self, event: Opcode | str, *, background: bool = False
    ) -> Callable[[Handler], Handler]: ...

    @overload
    def on(
        self, event: Opcode | str, fn: Handler, *, background: bool = False
    ) -> Handler: ...

    def on(
        self,
        event: Opcode | str,
        fn: Handler | None = None,
        *,
        background: bool = False,
    ) -> Handler | Callable[[Handler], Handler]:
        """注册事件处理器，语义与 EventEmitter.on 一致（装饰器/直传皆可）。"""
        if fn is None:
            return self._emitter.on(event, background=background)
        return self._emitter.on(event, fn, background=background)

    async def call_api(self, method: str, path: str, **kwargs: Any) -> Any:
        """通用 REST 入口：带 token 鉴权、429 退避重试与 401 自愈。

        类型化方法见 `bot.api`；本入口面向尚未封装的接口。
        """
        return await self.api.request(method, path, **kwargs)

    def _assemble(self) -> Connecter:
        """装配全部组件并按类型登记 services，返回就绪的连接器。"""
        http = ClientSession(timeout=self._config.timeout)
        session = Session()
        token = AccessToken(self._config, http)
        api = BotApi(self._config, http, token)
        self._http = http
        self._api = api
        self._emitter.services.update(
            {
                Bot: self,
                EventEmitter: self._emitter,
                EventQueue: self._emitter.queue,
                Config: self._config,
                Session: session,
                ClientSession: http,
                AccessToken: token,
                BotApi: api,
            }
        )

        # 各接入方式配自己的协议处理器：协议帧由适配器就近处理，
        # 只有业务事件（op=0）入队交给 emitter 分发（见 protocol.py）
        match self._config.connecter:
            case "websocket":
                protocol = WebsocketProtocol(self._config, session, token)
                connecter = WebsocketConnecter(
                    self._config, http, token, session, self._emitter.queue, protocol
                )
            case "webhook":
                protocol = WebhookProtocol(self._config)
                connecter = WebhookConnecter(
                    self._config, self._emitter.queue, protocol
                )
            case unknown:
                raise ValueError(f"未知的 CONNECTER: {unknown}")
        return connecter

    async def start(self) -> None:
        """装配并常驻运行，供嵌入外部 asyncio 应用；普通脚本直接用 run()。"""
        connecter = self._assemble()
        logger.info(f"qqbotsdk 启动，连接方式: {self._config.connecter}")
        try:
            await asyncio.gather(self._emitter.dispatch(), connecter.run())
        finally:
            # 在飞的后台 handler 先于连接池收尾，避免用到已关闭的 ClientSession
            await self._emitter.close()
            if self._http is not None:
                await self._http.close()

    def run(self) -> None:
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logger.info("qqbotsdk 已退出")
