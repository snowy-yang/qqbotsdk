"""用户信息模型 (2026-11-16 新增 ``GET /v2/users/{user_openid}/info``)."""

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class UserInfo(QQBotBaseModel):
    """用户基本信息.

    官方 2026-11-16 新增. 与 ``C2CUser``(事件里的发送者) 不同, 这里还带
    ``allow_proactive_msg``, 可以用来判断能否给该用户发主动消息.
    """

    union_openid: str | None = Field(
        default=None,
        description="跨应用关联用户 openid，当绑定了 3 方应用时有效",
    )
    username: str | None = Field(
        default=None,
        description="用户名",
    )
    avatar: str | None = Field(
        default=None,
        description="用户头像原图 URL",
    )
    allow_proactive_msg: bool | None = Field(
        default=None,
        description="是否接收主动推送，true 表示接受主动推送",
    )


class GetUserInfoResponse(UserInfo):
    """获取用户基本信息响应 (``GET /v2/users/{user_openid}/info``)."""


__all__ = [
    "GetUserInfoResponse",
    "UserInfo",
]
