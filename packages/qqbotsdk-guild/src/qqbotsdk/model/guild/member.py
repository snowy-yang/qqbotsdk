from pydantic import Field, RootModel

from qqbotsdk.model.core import QQBotBaseModel


class User(QQBotBaseModel):
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
        description="用户头像地址",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人",
    )
    union_openid: str | None = Field(
        None,
        description="跨应用统一用户 OpenID，需特殊申请；仅单独拉取成员信息时返回",
    )
    union_user_account: str | None = Field(
        None,
        description="机器人关联的互联应用的用户信息，需特殊申请",
    )


class Member(QQBotBaseModel):
    user: User | None = Field(
        None,
        description="用户对象",
    )
    nick: str | None = Field(
        None,
        description="频道昵称",
    )
    roles: list[str] | None = Field(
        None,
        description="身份组 ID 列表",
    )
    joined_at: str | None = Field(
        None,
        description="加入时间，ISO8601 格式",
    )
    deaf: bool | None = Field(
        None,
        description="是否被禁听",
    )
    mute: bool | None = Field(
        None,
        description="是否被禁言",
    )
    pending: bool | None = Field(
        None,
        description="是否待审核入频道",
    )


class GetGuildMembersRequest(QQBotBaseModel):
    after: str | None = Field(
        None,
        description="上一次回包中最后一个 member 的 user id，首次填 0",
    )
    limit: int | None = Field(
        None,
        description="分页大小 1-400，默认 1",
    )


class GetGuildMembersResponse(RootModel[list[Member]]):
    pass


class GetGuildMemberResponse(Member):
    pass


class RemoveGuildMemberRequest(QQBotBaseModel):
    add_blacklist: bool | None = Field(
        None,
        description="是否同时将用户加入频道黑名单",
    )
    delete_history_msg_days: int | None = Field(
        None,
        description="撤回该成员消息的时间范围，仅支持 3/7/15/30，-1 为撤回全部；0 不撤回",
    )


class Role(QQBotBaseModel):
    id: str = Field(
        ...,
        description="身份组 ID",
    )
    name: str | None = Field(
        None,
        description="身份组名称",
    )
    color: int | None = Field(
        None,
        description="ARGB 的 HEX 十六进制颜色值转换后的十进制数值",
    )
    hoist: int | None = Field(
        None,
        description="在成员列表中单独展示：0=否，1=是",
    )
    number: int | None = Field(
        None,
        description="身份组成员数量",
    )
    member_limit: int | None = Field(
        None,
        description="身份组成员上限",
    )


class GetGuildRolesResponse(QQBotBaseModel):
    guild_id: str | None = Field(
        None,
        description="频道 ID",
    )
    roles: list[Role] | None = Field(
        None,
        description="频道身份组列表",
    )
    role_num_limit: str | None = Field(
        None,
        description="默认分组上限",
    )


class CreateGuildRoleRequest(QQBotBaseModel):
    name: str | None = Field(
        None,
        description="身份组名称",
    )
    color: int | None = Field(
        None,
        description="ARGB 的 HEX 十六进制颜色值转换后的十进制数值",
    )
    hoist: int | None = Field(
        None,
        description="在成员列表中单独展示：0=否，1=是",
    )


class CreateGuildRoleResponse(QQBotBaseModel):
    role_id: str | None = Field(
        None,
        description="身份组 ID",
    )
    role: Role | None = Field(
        None,
        description="身份组对象",
    )


class UpdateGuildRoleRequest(QQBotBaseModel):
    name: str | None = Field(
        None,
        description="身份组名称",
    )
    color: int | None = Field(
        None,
        description="ARGB 的 HEX 十六进制颜色值转换后的十进制数值",
    )
    hoist: int | None = Field(
        None,
        description="在成员列表中单独展示：0=否，1=是",
    )


class UpdateGuildRoleResponse(QQBotBaseModel):
    guild_id: str | None = Field(
        None,
        description="频道 ID",
    )
    role_id: str | None = Field(
        None,
        description="身份组 ID",
    )
    role: Role | None = Field(
        None,
        description="修改后的身份组对象",
    )


class ChannelReference(QQBotBaseModel):
    id: str | None = Field(
        None,
        description="子频道 ID",
    )


class GuildMemberRoleRequest(QQBotBaseModel):
    channel: ChannelReference | None = Field(
        None,
        description="仅 role_id=5（子频道管理员）时传，指定具体子频道",
    )


class GetRoleMembersRequest(QQBotBaseModel):
    start_index: str | None = Field(
        None,
        description="上一次回包中的 next，首次填 0",
    )
    limit: int | None = Field(
        None,
        description="分页大小 1-400，默认 1",
    )


class GetRoleMembersResponse(QQBotBaseModel):
    data: list[Member] | None = Field(
        None,
        description="身份组成员列表",
    )
    next: str | None = Field(
        None,
        description="下一次请求的分页标识",
    )


class MuteRequest(QQBotBaseModel):
    mute_end_timestamp: str | None = Field(
        None,
        description="禁言到期时间戳，绝对时间戳，单位：秒；与 mute_seconds 同时赋值时以本字段为准",
    )
    mute_seconds: str | None = Field(
        None,
        description="禁言多少秒；解除禁言传 '0'",
    )


class MuteMembersRequest(MuteRequest):
    user_ids: list[str] = Field(
        ...,
        description="禁言成员的 user_id 列表，单次最多 20 个",
    )


class MuteMembersResponse(QQBotBaseModel):
    user_ids: list[str] | None = Field(
        None,
        description="设置成功的成员 user_id 列表",
    )
