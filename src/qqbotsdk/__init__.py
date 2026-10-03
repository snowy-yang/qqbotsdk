"""qqbotsdk：QQ 官方机器人 SDK 入口。

用法：`bot = Bot()` → `@bot.on(...)` 注册 handler → `bot.run()` 启动；
连接方式由 .env 的 CONNECTER 决定（websocket / webhook）。
架构详情见 docs/ARCHITECTURE.md。
"""

from dotenv import load_dotenv

from .api import BotApi
from .bot import Bot as Bot
from .config import Config as Config
from .connecter import Connecter as Connecter
from .connecter import WebhookConnecter, WebsocketConnecter
from .emitter import EventEmitter as EventEmitter
from .protocol import BaseProtocol as BaseProtocol
from .queue import EventQueue as EventQueue
from .session import Session as Session
from .token import AccessToken as AccessToken
from .webhook_protocol import WebhookProtocol as WebhookProtocol
from .ws_protocol import WebsocketProtocol as WebsocketProtocol

load_dotenv()

__all__ = [
    "AccessToken",
    "BaseProtocol",
    "Bot",
    "BotApi",
    "Config",
    "Connecter",
    "EventEmitter",
    "EventQueue",
    "Session",
    "WebhookConnecter",
    "WebhookProtocol",
    "WebsocketConnecter",
    "WebsocketProtocol",
]
