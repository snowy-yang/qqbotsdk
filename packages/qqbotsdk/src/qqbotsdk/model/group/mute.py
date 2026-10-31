from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class MuteScheduleRule(QQBotBaseModel):
    task_id: str | None = Field(
        None,
        description="任务 ID",
    )
    start_at: str | None = Field(
        None,
        description="禁言开始时间，RFC3339 格式",
    )
    end_at: str | None = Field(
        None,
        description="禁言结束时间，RFC3339 格式",
    )
    enabled: bool | None = Field(
        None,
        description="此规则是否启用",
    )


class MuteRecurringRule(QQBotBaseModel):
    task_id: str | None = Field(
        None,
        description="任务 ID",
    )
    weekdays: list[int] | None = Field(
        None,
        description="生效星期几列表，取值 1~7（1=周一）",
    )
    start_time: str | None = Field(
        None,
        description="时段开始时间，格式 HH:mm（北京时间）",
    )
    end_time: str | None = Field(
        None,
        description="时段结束时间，格式 HH:mm；小于 start_time 表示跨天",
    )
    enabled: bool | None = Field(
        None,
        description="此规则是否启用",
    )


class GlobalMuteRule(QQBotBaseModel):
    mode: str | None = Field(
        None,
        description="全员禁言模式：none=未开启，always=始终禁言，schedule=定时禁言",
    )
    schedule_rules: list[MuteScheduleRule] | None = Field(
        None,
        description="定时禁言规则列表",
    )
    recurring_rules: list[MuteRecurringRule] | None = Field(
        None,
        description="周期禁言规则列表",
    )


class MemberMuteState(QQBotBaseModel):
    member_openid: str | None = Field(
        None,
        description="被禁言成员的 openid",
    )
    mute_expire_at: str | None = Field(
        None,
        description="禁言到期时间，RFC3339 格式",
    )
    username: str | None = Field(
        None,
        description="被禁言成员的昵称",
    )
    union_openid: str | None = Field(
        None,
        description="跨应用统一标识（如有）",
    )


class GetGroupMuteStateResponse(QQBotBaseModel):
    global_rule: GlobalMuteRule | None = Field(
        None,
        description="群级禁言规则（全员禁言配置）",
    )
    members: list[MemberMuteState] | None = Field(
        None,
        description="当前处于禁言中的用户列表（不含已过期）",
    )


class SetMemberMuteState(QQBotBaseModel):
    op: str = Field(
        ...,
        description="操作类型：add=增加禁言，update=更新到期时间，del=解除禁言",
    )
    member_openid: str = Field(
        ...,
        description="被禁言成员的 openid；增加/更新时只能操作普通成员",
    )
    mute_expire_at: str | None = Field(
        None,
        description="禁言到期时间，RFC3339 格式；op=del 时可传空串",
    )


class SetGroupMuteStateRequest(QQBotBaseModel):
    members: list[SetMemberMuteState] = Field(
        ...,
        description="用户禁言列表，单次最多 20 个",
    )
