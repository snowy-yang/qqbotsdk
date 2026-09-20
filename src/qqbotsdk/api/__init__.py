"""OpenAPI 客户端：BotApi 按域组合——v2 群/单聊、频道消息、频道管理。

各域模块是方法集（继承 BaseApi 共享请求内核：鉴权头注入、429 自动
重试、401 刷新 token 重试、统一 ApiError），方法名与拆分前完全一致。
"""

from .channel import ChannelApi
from .core import ApiError
from .core import BaseApi as BaseApi
from .guild import GuildApi
from .v2 import V2Api, button, keyboard


class BotApi(V2Api, ChannelApi, GuildApi):
    """通用 REST 封装；具体业务接口见各域方法集。

    BaseApi（请求内核）经域方法集继承自然落在 MRO 末尾，
    构造签名 (config, http, token) 由它提供。
    """


__all__ = [
    "ApiError",
    "BotApi",
    "ChannelApi",
    "GuildApi",
    "V2Api",
    "button",
    "keyboard",
]
