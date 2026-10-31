from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class GetAppAccessTokenRequest(QQBotBaseModel):
    app_id: str = Field(
        ...,
        alias="appId",
        description="在开放平台管理端上获得。",
    )
    client_secret: str = Field(
        ...,
        alias="clientSecret",
        description="在开放平台管理端上获得。",
    )


class GetAppAccessTokenResponse(QQBotBaseModel):
    access_token: str = Field(
        ...,
        description="获取到的凭证。",
    )
    expires_in: int = Field(
        ...,
        description="凭证有效时间，单位：秒。目前是 7200 秒之内的值。",
    )
