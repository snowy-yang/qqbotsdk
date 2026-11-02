from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class MuteScheduleRule(QQBotBaseModel):
    task_id: str | None = Field(
        default=None,
        description="任务 ID，用于标记此定时禁言任务",
    )
    start_at: str | None = Field(
        default=None,
        description="禁言开始时间，RFC3339 格式",
    )
    end_at: str | None = Field(
        default=None,
        description="禁言结束时间，RFC3339 格式",
    )
    enabled: bool | None = Field(
        default=None,
        description="此规则是否启用",
    )


class MuteRecurringRule(QQBotBaseModel):
    task_id: str | None = Field(
        default=None,
        description="任务 ID，用于标记此周期禁言规则",
    )
    weekdays: list[int] | None = Field(
        default=None,
        description="生效星期几列表，取值 1~7（1=周一，7=周日），可多选",
    )
    start_time: str | None = Field(
        default=None,
        description="时段开始时间，格式 HH:mm（北京时间）",
    )
    end_time: str | None = Field(
        default=None,
        description="时段结束时间，格式 HH:mm（北京时间）；小于 start_time 表示跨天到次日",
    )
    enabled: bool | None = Field(
        default=None,
        description="此规则是否启用",
    )


class GlobalMuteRule(QQBotBaseModel):
    mode: Literal["none", "always", "schedule"] | None = Field(
        default=None,
        description="全员禁言模式：none=未开启，always=始终禁言，schedule=定时禁言（定时和周期性）",
    )
    schedule_rules: list[MuteScheduleRule] | None = Field(
        default=None,
        description="定时禁言规则列表，可包含多条",
    )
    recurring_rules: list[MuteRecurringRule] | None = Field(
        default=None,
        description="周期禁言规则列表，可包含多条",
    )


class MemberMuteState(QQBotBaseModel):
    member_openid: str | None = Field(
        default=None,
        description="被禁言成员的 openid",
    )
    mute_expire_at: str | None = Field(
        default=None,
        description="禁言到期时间，RFC3339 格式",
    )
    username: str | None = Field(
        default=None,
        description="被禁言成员的昵称",
    )
    union_openid: str | None = Field(
        default=None,
        description="用户在应用/开放平台下的统一标识（如有）",
    )


class GetGroupMuteStateResponse(QQBotBaseModel):
    global_rule: GlobalMuteRule | None = Field(
        default=None,
        description="群级禁言规则（全员禁言配置）",
    )
    members: list[MemberMuteState] | None = Field(
        default=None,
        description="当前处于禁言中的用户列表（不含已过期）",
    )


class SetMemberMuteState(QQBotBaseModel):
    op: Literal["add", "update", "del"] = Field(
        ...,
        description="操作类型：add=增加禁言，update=更新禁言到期时间，del=解除禁言",
    )
    member_openid: str = Field(
        ...,
        description="被禁言成员的 openid；增加/更新时只能操作普通成员，不能操作群主、管理员、机器人",
    )
    mute_expire_at: str | None = Field(
        default=None,
        description="禁言到期时间，RFC3339 格式；op=del 时可传空串表示立即解除禁言",
    )


class SetGroupMuteStateRequest(QQBotRequestModel):
    members: list[SetMemberMuteState] | None = Field(
        default=None,
        max_length=20,
        description="用户禁言列表，每项通过 op 控制增/改/删，单次设置不能超过 20 个",
    )
