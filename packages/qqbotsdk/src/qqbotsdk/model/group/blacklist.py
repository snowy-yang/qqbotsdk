from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class BlacklistUser(QQBotBaseModel):
    union_openid: str | None = Field(
        default=None,
        description="用户在应用/开放平台下的统一标识（如有）",
    )
    member_openid: str | None = Field(
        default=None,
        description="用户 openid",
    )
    username: str | None = Field(
        default=None,
        description="用户昵称",
    )
    banned_at: str | None = Field(
        default=None,
        description="拉黑时间戳，RFC3339 格式",
    )
    bot: bool | None = Field(
        default=None,
        description="是否为机器人账号",
    )


class GetGroupBlacklistRequest(QQBotRequestModel):
    cursor: str | None = Field(
        default=None,
        description="分页游标，首次请求可不传或传空串",
    )
    limit: int | None = Field(
        default=None,
        le=100,
        description="单页数量，默认 20，最大 100",
    )


class GetGroupBlacklistResponse(QQBotBaseModel):
    users: list[BlacklistUser] | None = Field(
        default=None,
        description="黑名单用户列表",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，空串表示已到末页",
    )


class UpdateGroupBlacklistRequest(QQBotRequestModel):
    op: Literal["add", "del"] = Field(
        ...,
        description="操作类型：add=加入黑名单（目标成员在群中时无法加入），del=移出黑名单",
    )
    member_openids: list[str] = Field(
        ...,
        max_length=20,
        description="目标成员 openid 列表，单次最多 20 个",
    )


class UpdateGroupBlacklistResponse(QQBotBaseModel):
    fail_openids: list[str] | None = Field(
        default=None,
        description="op=add 时返回拉黑失败的 openid 列表，op=del 时同义",
    )
