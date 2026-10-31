from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class BlacklistUser(QQBotBaseModel):
    union_openid: str | None = Field(
        None,
        description="跨应用统一标识（如有）",
    )
    member_openid: str | None = Field(
        None,
        description="用户 openid",
    )
    username: str | None = Field(
        None,
        description="用户昵称",
    )
    banned_at: str | None = Field(
        None,
        description="拉黑时间戳，RFC3339 格式",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人账号",
    )


class GetGroupBlacklistRequest(QQBotBaseModel):
    cursor: str | None = Field(
        None,
        description="分页游标，首次不传",
    )
    limit: int | None = Field(
        None,
        description="单页数量，默认 20，最大 100",
    )


class GetGroupBlacklistResponse(QQBotBaseModel):
    users: list[BlacklistUser] | None = Field(
        None,
        description="黑名单用户列表",
    )
    next_cursor: str | None = Field(
        None,
        description="下一页游标，空串表示已到末页",
    )


class UpdateGroupBlacklistRequest(QQBotBaseModel):
    op: str = Field(
        ...,
        description="操作类型：add=加入黑名单，del=移出黑名单",
    )
    member_openids: list[str] = Field(
        ...,
        description="目标成员 openid 列表，单次最多 20 个",
    )


class UpdateGroupBlacklistResponse(QQBotBaseModel):
    fail_openids: list[str] | None = Field(
        None,
        description="操作失败的 openid 列表",
    )
