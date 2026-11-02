"""互动事件模型 (INTERACTION_CREATE).

注意与 ``qqbotsdk.model.interaction`` 区分: 那个模块是**接口请求模型**
(回应互动用的 ``ConfirmInteractionsRequest``), 这里建模的是**事件对象**.

模型只描述网关帧的 ``d`` 字段, 信封由 ``qqbotsdk.ws.payload.GatewayPayload``
承载.
"""

from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class InteractionMessageScene(QQBotBaseModel):
    """互动消息场景信息."""

    ext: list[str] | None = Field(
        default=None,
        description='扩展信息键值对列表，如 "disable_net_search=1" 表示关闭联网搜索',
    )


class InteractionAuthorizeData(QQBotBaseModel):
    """用户/群授权数据, 仅 type=18/19/20 授权相关事件."""

    opt_scene: Literal["setting", "dialog"] | None = Field(
        default=None,
        description="授权操作场景：setting=资料页设置，dialog=弹窗授权",
    )
    scope: Literal["c2c_push", "group_push"] | None = Field(
        default=None,
        description="授权范围：c2c_push=C2C 主动消息推送，group_push=群主动消息推送",
    )


class InteractionResolved(QQBotBaseModel):
    """解析后的互动数据."""

    button_data: str | None = Field(
        default=None,
        description="按钮的 data 字段值（发送消息按钮时设置）；消息反馈场景下为回调数据",
    )
    button_id: str | None = Field(
        default=None,
        description="按钮的 id 字段值（发送消息按钮时设置）",
    )
    user_id: str | None = Field(
        default=None,
        description="操作用户 ID（仅频道场景有值）",
    )
    feature_id: str | None = Field(
        default=None,
        description="功能 ID（仅快捷菜单有值，管理端设置）",
    )
    message_id: str | None = Field(
        default=None,
        description="操作的消息 ID（频道场景为消息 OpenID；消息反馈场景为机器人消息 ID）",
    )
    feedback_opt: Literal["LIKE", "UNLIKE"] | None = Field(
        default=None,
        description="反馈选项（仅 type=13 消息反馈）：LIKE=点赞，UNLIKE=点踩",
    )
    checked: int | None = Field(
        default=None,
        description="反馈选项是否选中（仅 type=13 消息反馈）",
    )
    action: str | None = Field(
        default=None,
        description="操作类型：type=15 故事集为 ENTER_STORY=进入 / QUIT_STORY=退出；type=16 切换模型为对应操作动作",
    )
    message_scene: InteractionMessageScene | None = Field(
        default=None,
        description="消息场景信息（仅 type=13 消息反馈）",
    )
    authorize_data: InteractionAuthorizeData | None = Field(
        default=None,
        description="授权数据（仅 type=18/19/20 用户/群授权事件）",
    )


class InteractionData(QQBotBaseModel):
    """互动数据."""

    type: int | None = Field(
        default=None,
        description="互动数据类型：11=消息按钮点击，12=快捷菜单点击，13=消息反馈点击，14=清空会话点击，15=故事集点击，16=切换模型点击",
    )
    resolved: InteractionResolved | None = Field(
        default=None,
        description="解析后的互动数据",
    )


class InteractionCreateEvent(QQBotBaseModel):
    """用户与机器人的互动操作触发 (INTERACTION_CREATE).

    仅 ``type=11``(消息按钮) 与 ``type=12``(快捷菜单) 需要调用
    ``PUT /interactions/{interaction_id}`` 回应, 其他类型无需回应.
    """

    id: str | None = Field(
        default=None,
        description="事件 ID，用于被动消息发送和互动回调",
    )
    type: int | None = Field(
        default=None,
        description="互动类型：11=消息按钮回调，12=单聊快捷菜单回调，13=消息反馈，14=清空会话，15=进出故事集，16=切换模型，18=用户授权，19=群授权，20=群授权状态变更",
    )
    scene: Literal["c2c", "group", "guild"] | None = Field(
        default=None,
        description="事件发生场景：c2c=单聊，group=群聊，guild=频道",
    )
    chat_type: Literal[0, 1, 2] | None = Field(
        default=None,
        description="聊天场景：0=频道，1=群聊，2=单聊",
    )
    timestamp: str | None = Field(
        default=None,
        description="触发时间，RFC3339 格式",
    )
    guild_id: str | None = Field(
        default=None,
        description="频道 OpenID（仅频道场景有值）",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 OpenID（仅频道场景有值）",
    )
    user_openid: str | None = Field(
        default=None,
        description="用户 OpenID（仅单聊场景有值）",
    )
    group_openid: str | None = Field(
        default=None,
        description="群 OpenID（仅群聊场景有值）",
    )
    group_member_openid: str | None = Field(
        default=None,
        description="群成员 OpenID（仅群聊场景有值）",
    )
    data: InteractionData | None = Field(
        default=None,
        description="互动数据",
    )
    version: int | None = Field(
        default=None,
        description="版本号，默认 1",
    )
    application_id: str | None = Field(
        default=None,
        description="机器人 AppID",
    )


__all__ = [
    "InteractionAuthorizeData",
    "InteractionCreateEvent",
    "InteractionData",
    "InteractionMessageScene",
    "InteractionResolved",
]
