"""依赖装配：dishka 容器的 provider 定义与 ADAPTERS 接线表。

所有组件均为 APP scope 单例；按 CONNECTER 环境变量动态 provide
具体的连接适配器与协议处理器。业务代码注入用 `Inject[T]`（FromDishka
别名），裸标注 `Event`/`Session`/`BotApi` 也可直接解析。
"""

from collections.abc import AsyncIterator

from aiohttp import ClientSession
from dishka import (
    AsyncContainer,
    FromDishka,
    Provider,
    Scope,
    from_context,
    make_async_container,
    provide,
)

from .api import BotApi
from .config import Config
from .connecter import Connecter, WebhookConnecter, WebsocketConnecter
from .emitter import BaseProtocol, EventEmitter
from .events import Event
from .queue import EventQueue
from .session import Session
from .token import AccessToken
from .webhook_protocol import WebhookProtocol
from .ws_protocol import WebsocketProtocol

Inject = FromDishka

# 接入方式 → (连接适配器, 协议处理器)，均由 dishka 按构造签名自动装配
ADAPTERS: dict[str, tuple[type[Connecter], type[BaseProtocol]]] = {
    "websocket": (WebsocketConnecter, WebsocketProtocol),
    "webhook": (WebhookConnecter, WebhookProtocol),
}


class AppProvider(Provider):
    event = from_context(Event, scope=Scope.REQUEST)

    @provide(scope=Scope.APP)
    def get_config(self) -> Config:
        return Config.load()

    @provide(scope=Scope.APP)
    def get_session(self) -> Session:
        return Session()

    @provide(scope=Scope.APP)
    def get_token(self, config: Config, http: ClientSession) -> AccessToken:
        return AccessToken(config, http)

    @provide(scope=Scope.APP)
    def get_api(
        self, config: Config, http: ClientSession, token: AccessToken
    ) -> BotApi:
        return BotApi(config, http, token)

    @provide(scope=Scope.APP)
    async def get_http(self, config: Config) -> AsyncIterator[ClientSession]:
        # 全 SDK 共享一个连接池，随容器关闭
        session = ClientSession(timeout=config.timeout)
        yield session
        await session.close()


def make_container(emitter: EventEmitter | None = None) -> AsyncContainer:
    """构建 DI 容器。传入外部构造的 EventEmitter 时，容器复用该实例及其队列，
    保证用户在 main() 之前注册的 handler 与主体是同一个 emitter。"""
    if emitter is None:
        emitter = EventEmitter(EventQueue())

    provider = AppProvider()
    provider.provide(lambda: emitter, provides=EventEmitter, scope=Scope.APP)
    provider.provide(lambda: emitter.queue, provides=EventQueue, scope=Scope.APP)

    connecter_cls, protocol_cls = ADAPTERS[Config.load().connecter]
    provider.provide(protocol_cls, provides=BaseProtocol, scope=Scope.APP)
    provider.provide(connecter_cls, provides=Connecter, scope=Scope.APP)
    return make_async_container(provider)
