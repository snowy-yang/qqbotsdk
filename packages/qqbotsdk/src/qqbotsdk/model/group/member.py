from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class GroupInfo(QQBotBaseModel):
    group_openid: str | None = Field(
        default=None,
        description="群 OpenID",
    )
    group_name: str | None = Field(
        default=None,
        description="群名称",
    )
    group_finger_memo: str | None = Field(
        default=None,
        description="群简介",
    )
    group_class_text: str | None = Field(
        default=None,
        description="群分类",
    )
    group_tags: list[str] | None = Field(
        default=None,
        description="群标签列表",
    )
    group_member_num: int | None = Field(
        default=None,
        description="群成员人数",
    )


class GetGroupInfoResponse(GroupInfo):
    pass


class GroupMember(QQBotBaseModel):
    member_openid: str | None = Field(
        default=None,
        description="成员 OpenID",
    )
    username: str | None = Field(
        default=None,
        description="用户昵称",
    )
    member_role: Literal["member", "owner", "admin"] | None = Field(
        default=None,
        description="群成员角色：member=普通成员，owner=群主，admin=管理员",
    )
    bot: bool | None = Field(
        default=None,
        description="是否机器人",
    )
    joined_at: str | None = Field(
        default=None,
        description="入群时间戳，RFC3339 格式",
    )
    union_openid: str | None = Field(
        default=None,
        description="用户在应用/开放平台下的统一标识（如有）",
    )


class GetGroupMembersRequest(QQBotRequestModel):
    cursor: str | None = Field(
        default=None,
        description="分页游标，首次不传或传空串，后续传上次响应的 next_cursor",
    )


class GetGroupMembersResponse(QQBotBaseModel):
    members: list[GroupMember] | None = Field(
        default=None,
        description="成员列表，每次最多返回 30 条",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，空串表示已到末页",
    )


class GetGroupMemberResponse(GroupMember):
    pass


class GroupBotState(QQBotBaseModel):
    member_openid: str | None = Field(
        default=None,
        description="机器人的 openid",
    )
    joined_at: str | None = Field(
        default=None,
        description="入群时间戳，RFC3339 格式",
    )
    allow_proactive_msg: bool | None = Field(
        default=None,
        description="是否接收主动推送，true 表示接受主动推送",
    )
    recv_msg_setting: str | None = Field(
        default=None,
        description="群内接收消息的设置：all、only_mention、mention_and_context",
    )
    member_role: Literal["member", "owner", "admin"] | None = Field(
        default=None,
        description="群成员角色：member=普通成员，owner=群主，admin=管理员",
    )


class GetGroupBotStateResponse(GroupBotState):
    pass


class RemoveGroupMembersRequest(QQBotRequestModel):
    member_openids: list[str] = Field(
        ...,
        max_length=20,
        description="需要移除的成员 openid 列表，单次最多 20 个",
    )
    add_to_member_blacklist: bool | None = Field(
        default=None,
        description="是否同时加入群黑名单，默认 false",
    )


class RemoveGroupMembersResponse(QQBotBaseModel):
    remove_members_result: str | None = Field(
        default=None,
        description="成功时返回 success",
    )
    add_to_member_blacklist_fail_openids: list[str] | None = Field(
        default=None,
        description="拉黑失败的 openid",
    )
