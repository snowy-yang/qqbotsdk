"""qqbotsdk：QQ 官方机器人 SDK 入口。

用法：`bot = Bot()` → `@bot.on(...)` 注册 handler → `bot.run()` 启动；
通过 WebSocket 长连接接入 QQ 开放平台。
架构详情见 docs/ARCHITECTURE.md。
"""

from dotenv import load_dotenv

from .api import BotApi
from .bot import Bot as Bot
from .config import Config as Config
from .connecter import Connecter as Connecter
from .emitter import EventEmitter as EventEmitter
from .model import Intent as Intent
from .protocol import Protocol as Protocol
from .queue import EventQueue as EventQueue
from .session import Session as Session
from .token import AccessToken as AccessToken

load_dotenv()

__all__ = [
    "AccessToken",
    "Bot",
    "BotApi",
    "Config",
    "Connecter",
    "EventEmitter",
    "EventQueue",
    "Intent",
    "Protocol",
    "Session",
]
