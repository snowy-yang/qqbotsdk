from pydantic import Field, RootModel

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class Guild(QQBotBaseModel):
    id: str = Field(
        ...,
        description="频道 ID",
    )
    name: str | None = Field(
        default=None,
        description="频道名称",
    )
    icon: str | None = Field(
        default=None,
        description="频道头像 URL",
    )
    owner_id: str | None = Field(
        default=None,
        description="创建者用户 ID",
    )
    owner: bool | None = Field(
        default=None,
        description="当前机器人是否为创建者",
    )
    member_count: int | None = Field(
        default=None,
        description="成员数",
    )
    max_members: int | None = Field(
        default=None,
        description="最大成员数",
    )
    description: str | None = Field(
        default=None,
        description="频道描述",
    )
    joined_at: str | None = Field(
        default=None,
        description="加入时间，ISO8601 格式",
    )


class GetGuildResponse(Guild):
    pass


class GetMeGuildsRequest(QQBotRequestModel):
    before: str | None = Field(
        default=None,
        description="读取此 guild_id 之前的数据，设置时先反序再分页",
    )
    after: str | None = Field(
        default=None,
        description="读取此 guild_id 之后的数据，与 before 同时设置时 after 无效",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="每次拉取条数，默认 100，最大 100",
    )


class GetMeGuildsResponse(RootModel[list[Guild]]):
    pass


class GuildMessageSetting(QQBotBaseModel):
    disable_create_dm: bool | None = Field(
        default=None,
        description="是否禁止创建私信",
    )
    disable_push_msg: bool | None = Field(
        default=None,
        description="是否禁止主动推送消息",
    )
    channel_ids: list[str] | None = Field(
        default=None,
        description="可主动推送的子频道 ID 列表",
    )
    channel_push_max_num: int | None = Field(
        default=None,
        description="每个子频道每天可推送的消息数",
    )


class GetGuildMessageSettingResponse(GuildMessageSetting):
    pass


class APIPermission(QQBotBaseModel):
    path: str | None = Field(
        default=None,
        description="接口路径",
    )
    method: str | None = Field(
        default=None,
        description="HTTP 方法",
    )
    desc: str | None = Field(
        default=None,
        description="接口描述",
    )
    auth_status: int | None = Field(
        default=None,
        description="授权状态：0=未授权，1=已授权",
    )


class GetGuildApiPermissionsResponse(QQBotBaseModel):
    apis: list[APIPermission] | None = Field(
        default=None,
        description="机器人可用权限列表",
    )


class ApiPermissionDemandIdentify(QQBotBaseModel):
    path: str | None = Field(
        default=None,
        description="要申请的接口路径，如 /guilds/{guild_id}",
    )
    method: str | None = Field(
        default=None,
        description="要申请的接口 HTTP 方法",
    )


class CreateApiPermissionDemandRequest(QQBotRequestModel):
    channel_id: str = Field(
        ...,
        description="授权链接发送的子频道 ID",
    )
    api_identify: ApiPermissionDemandIdentify = Field(
        ...,
        description="API 权限需求标识",
    )
    desc: str = Field(
        ...,
        description="申请权限后可实现功能的描述",
    )


class CreateApiPermissionDemandResponse(QQBotBaseModel):
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    api_identify: ApiPermissionDemandIdentify | None = Field(
        default=None,
        description="API 权限需求标识",
    )
    title: str | None = Field(
        default=None,
        description="授权链接标题",
    )
    desc: str | None = Field(
        default=None,
        description="申请权限说明",
    )
