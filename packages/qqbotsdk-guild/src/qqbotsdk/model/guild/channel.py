from pydantic import Field, RootModel

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class Channel(QQBotBaseModel):
    id: str = Field(
        ...,
        description="子频道 ID",
    )
    guild_id: str | None = Field(
        default=None,
        description="所属频道 ID",
    )
    name: str | None = Field(
        default=None,
        description="子频道名",
    )
    type: int | None = Field(
        default=None,
        description="子频道类型：0=文字，2=语音，4=分组，10005=直播，10006=应用，10007=论坛",
    )
    sub_type: int | None = Field(
        default=None,
        description="子频道子类型：0=闲聊，1=公告，2=攻略，3=开黑",
    )
    position: int | None = Field(
        default=None,
        description="排序值，从 1 开始",
    )
    parent_id: str | None = Field(
        default=None,
        description="所属分组 ID，仅对子频道有效，对子频道分组（type=4）无效",
    )
    owner_id: str | None = Field(
        default=None,
        description="创建人 ID",
    )
    private_type: int | None = Field(
        default=None,
        description="私密类型：0=公开，1=群主管理员可见，2=群主管理员+指定成员",
    )
    speak_permission: int | None = Field(
        default=None,
        description="发言权限：0=无效，1=所有人，2=群主管理员+指定成员",
    )
    application_id: str | None = Field(
        default=None,
        description="应用子频道标识",
    )
    permissions: str | None = Field(
        default=None,
        description="用户拥有的子频道权限位图",
    )


class GetChannelResponse(Channel):
    pass


class GetGuildChannelsResponse(RootModel[list[Channel]]):
    pass


class CreateChannelRequest(QQBotRequestModel):
    name: str | None = Field(
        default=None,
        description="子频道名称",
    )
    type: int | None = Field(
        default=None,
        description="子频道类型：0=文字，2=语音，4=分组，10005=直播，10006=应用，10007=论坛",
    )
    sub_type: int | None = Field(
        default=None,
        description="子频道子类型：0=闲聊，1=公告，2=攻略，3=开黑",
    )
    position: int | None = Field(
        default=None,
        description="排序值；分组类型（type=4）必须 >= 2",
    )
    parent_id: str | None = Field(
        default=None,
        description="所属分组 ID",
    )
    private_type: int | None = Field(
        default=None,
        description="私密类型：0=公开，1=群主管理员可见，2=群主管理员+指定成员",
    )
    private_user_ids: list[str] | None = Field(
        default=None,
        description="私密成员 ID 列表",
    )
    speak_permission: int | None = Field(
        default=None,
        description="发言权限：0=无效，1=所有人，2=群主管理员+指定成员",
    )
    application_id: str | None = Field(
        default=None,
        description="应用子频道 AppID，仅应用子频道需要",
    )


class CreateChannelResponse(Channel):
    pass


class UpdateChannelRequest(QQBotRequestModel):
    name: str | None = Field(
        default=None,
        description="子频道名",
    )
    position: int | None = Field(
        default=None,
        description="排序值",
    )
    parent_id: str | None = Field(
        default=None,
        description="所属分组 ID",
    )
    private_type: int | None = Field(
        default=None,
        description="私密类型：0=公开，1=群主管理员可见，2=群主管理员+指定成员",
    )
    speak_permission: int | None = Field(
        default=None,
        description="发言权限：0=无效，1=所有人，2=群主管理员+指定成员",
    )


class UpdateChannelResponse(Channel):
    pass


class GetChannelOnlineNumsResponse(QQBotBaseModel):
    online_nums: int | None = Field(
        default=None,
        description="子频道在线成员数",
    )


class ChannelPermissions(QQBotBaseModel):
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    user_id: str | None = Field(
        default=None,
        description="用户 ID",
    )
    role_id: str | None = Field(
        default=None,
        description="身份组 ID",
    )
    permissions: str | None = Field(
        default=None,
        description="字符串形式的权限位图",
    )


class GetChannelPermissionsResponse(ChannelPermissions):
    pass


class GetChannelRolePermissionsResponse(ChannelPermissions):
    pass


class UpdateChannelPermissionsRequest(QQBotRequestModel):
    add: str | None = Field(
        default=None,
        description="字符串形式的位图，表示赋予的权限",
    )
    remove: str | None = Field(
        default=None,
        description="字符串形式的位图，表示删除的权限",
    )
