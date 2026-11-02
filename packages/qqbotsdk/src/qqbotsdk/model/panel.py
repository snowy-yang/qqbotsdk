from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel

# 面板生效场景
PANEL_SCOPE_C2C = "c2c"
PANEL_SCOPE_GROUP = "group"
PANEL_SCOPE_CHANNEL = "channel"
PANEL_SCOPE_DM = "dm"

# 面板生效范围
PANEL_TARGET_ALL = "all"
PANEL_TARGET_SPECIFIC = "specific"

# 面板元素类型
PANEL_ITEM_COMMAND = "command"
PANEL_ITEM_LINK = "link"

# 关联对象操作
PANEL_TARGET_OP_ADD = "add"
PANEL_TARGET_OP_DEL = "del"


class PanelItem(QQBotBaseModel):
    name: str | None = Field(
        default=None,
        description="元素名称，最多 14 个字符，约 7 个中文汉字；type=command 时点击后填入聊天输入框，type=link 时仅用于展示",
    )
    desc: str | None = Field(
        default=None,
        description="元素描述，最多 30 个字符，约 15 个中文汉字，在面板中展示给用户",
    )
    type: Literal["command", "link"] | None = Field(
        default=None,
        description="元素类型：command=指令，link=链接跳转",
    )
    only_admin: bool | None = Field(
        default=None,
        description="是否仅管理员可操作",
    )
    link: str | None = Field(
        default=None,
        description="跳转链接，仅 type=link 时有效",
    )


class Panel(QQBotBaseModel):
    items: list[PanelItem] | None = Field(
        default=None,
        description="面板元素列表，最多 20 个",
    )
    remark: str | None = Field(
        default=None,
        description="面板备注，最多 255 个字符，不对用户展示",
    )
    version: int | None = Field(
        default=None,
        description="当前版本号",
    )


class GetPanelsRequest(QQBotRequestModel):
    scope: Literal["c2c", "group", "channel", "dm"] = Field(
        ...,
        description="生效场景，必须传：c2c=单聊，group=群聊，channel=文字子频道，dm=频道私信",
    )
    cursor: str | None = Field(
        default=None,
        description="分页游标，首次不传，后续传上次响应的 next_cursor",
    )
    limit: int | None = Field(
        default=None,
        le=50,
        description="每页拉取条数，默认 20，最大 50",
    )


class PanelRecord(QQBotBaseModel):
    panel_id: str | None = Field(
        default=None,
        description="面板 ID",
    )
    scope: Literal["c2c", "group", "channel", "dm"] | None = Field(
        default=None,
        description="生效场景：c2c=单聊，group=群聊，channel=文字子频道，dm=频道私信",
    )
    target_type: Literal["all", "specific"] | None = Field(
        default=None,
        description="作用范围：all=全局配置，specific=指定用户/群生效，仅 c2c/group 场景可能为 specific",
    )
    panel: Panel | None = Field(
        default=None,
        description="面板配置内容",
    )
    created_at: str | None = Field(
        default=None,
        description="面板创建时间，RFC3339 格式",
    )
    updated_at: str | None = Field(
        default=None,
        description="面板更新时间，RFC3339 格式",
    )
    version: int | None = Field(
        default=None,
        description="面板版本号",
    )


class GetPanelsResponse(QQBotBaseModel):
    records: list[PanelRecord] | None = Field(
        default=None,
        description="面板记录列表，按设置时间倒序",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，空串表示已到最后一页",
    )
    is_end: bool | None = Field(
        default=None,
        description="是否已拉取到最后一页",
    )


class CreatePanelRequest(QQBotRequestModel):
    scope: Literal["c2c", "group", "channel", "dm"] = Field(
        ...,
        description="生效场景；channel 和 dm 仅支持 target_type=all",
    )
    target_type: Literal["all", "specific"] | None = Field(
        default=None,
        description="作用范围；仅 c2c 和 group 支持 specific",
    )
    user_openids: list[str] | None = Field(
        default=None,
        description="用户 openid 列表，仅 c2c + specific 时有效，最多 20 个",
    )
    group_openids: list[str] | None = Field(
        default=None,
        description="群 openid 列表，仅 group + specific 时有效，最多 20 个",
    )
    panel: Panel = Field(
        ...,
        description="面板配置内容",
    )


class CreatePanelResponse(QQBotBaseModel):
    panel_id: str = Field(
        ...,
        description="新创建的面板 ID",
    )


class GetPanelResponse(QQBotBaseModel):
    panel_id: str | None = Field(
        default=None,
        description="面板 ID",
    )
    scope: Literal["c2c", "group", "channel", "dm"] | None = Field(
        default=None,
        description="生效场景：c2c=单聊，group=群聊，channel=文字子频道，dm=频道私信",
    )
    target_type: Literal["all", "specific"] | None = Field(
        default=None,
        description="作用范围：all=全局配置，specific=指定用户/群生效，仅 c2c/group 场景可能为 specific",
    )
    panel: Panel | None = Field(
        default=None,
        description="面板配置内容",
    )
    created_at: str | None = Field(
        default=None,
        description="面板创建时间，RFC3339 格式",
    )
    updated_at: str | None = Field(
        default=None,
        description="面板更新时间，RFC3339 格式",
    )
    version: int | None = Field(
        default=None,
        description="面板版本号",
    )
    user_openids: list[str] | None = Field(
        default=None,
        description="关联的用户 openid 列表，仅 c2c + specific 时返回，最多 1000 条",
    )
    group_openids: list[str] | None = Field(
        default=None,
        description="关联的群 openid 列表，仅 group + specific 时返回，最多 1000 条",
    )


class UpdatePanelRequest(QQBotRequestModel):
    panel: Panel = Field(
        ...,
        description="面板配置内容，会覆盖原有元素列表与备注，不影响已关联对象",
    )


class UpdatePanelResponse(QQBotBaseModel):
    version: int | None = Field(
        default=None,
        description="本次修改后的面板版本号",
    )


class UpdatePanelTargetRequest(QQBotRequestModel):
    op: Literal["add", "del"] = Field(
        ...,
        description="操作类型：add=添加关联对象，del=移除关联对象",
    )
    user_openids: list[str] | None = Field(
        default=None,
        description="用户 openid 列表，仅 c2c 场景有效，最多 20 个",
    )
    group_openids: list[str] | None = Field(
        default=None,
        description="群 openid 列表，仅 group 场景有效，最多 20 个",
    )
