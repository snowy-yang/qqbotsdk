from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class GetGatewayResponse(QQBotBaseModel):
    url: str = Field(
        ...,
        description="WebSocket 连接地址",
    )


class GetMeResponse(QQBotBaseModel):
    id: str = Field(
        ...,
        description="用户 ID",
    )
    username: str | None = Field(
        None,
        description="用户名",
    )
    avatar: str | None = Field(
        None,
        description="头像 URL",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人",
    )
    union_openid: str | None = Field(
        None,
        description="跨应用统一用户 OpenID，需特殊申请",
    )
    union_user_account: str | None = Field(
        None,
        description="跨应用统一用户账号，需特殊申请",
    )
    share_url: str | None = Field(
        None,
        description="机器人分享链接",
    )
    welcome_msg: str | None = Field(
        None,
        description="欢迎语",
    )


class GenerateUrlLinkRequest(QQBotBaseModel):
    callback_data: str | None = Field(
        None,
        description="回传给机器人后台的数据，最长 32 字符",
    )


class GenerateUrlLinkData(QQBotBaseModel):
    url: str | None = Field(
        None,
        description="生成的分享链接",
    )


class GenerateUrlLinkResponse(QQBotBaseModel):
    data: GenerateUrlLinkData | None = Field(
        None,
        description="分享链接数据",
    )
