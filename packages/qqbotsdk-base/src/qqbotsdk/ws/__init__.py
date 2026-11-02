"""网关 WebSocket 客户端.

对外只需要几个名字: ``Intents``(事件订阅位), ``DEFAULT_INTENTS``(默认订阅),
``GatewayPayload``(事件数据包), ``ReadyContent``(READY 事件体),
``QQBotWebSocket``(连接客户端), ``WILDCARD_EVENT``(通配事件名) 与 ``Handler``(回调类型).
"""

from qqbotsdk.ws.client import WILDCARD_EVENT, Handler, QQBotWebSocket
from qqbotsdk.ws.intents import DEFAULT_INTENTS, Intents
from qqbotsdk.ws.payload import GatewayPayload, OpCode, ReadyContent, ReadyUser

__all__ = [
    "DEFAULT_INTENTS",
    "WILDCARD_EVENT",
    "GatewayPayload",
    "Handler",
    "Intents",
    "OpCode",
    "QQBotWebSocket",
    "ReadyContent",
    "ReadyUser",
]
