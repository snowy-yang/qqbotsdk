from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class JoinApprovalStrategy(QQBotBaseModel):
    strategy_id: str | None = Field(
        default=None,
        description="策略 ID",
    )
    group_openids: list[str] | None = Field(
        default=None,
        description="关联的群 openid 列表，创建时使用 group_openids 时返回",
    )
    group_ids: list[str] | None = Field(
        default=None,
        description="关联的 QQ 群号列表，创建时使用 group_ids 时返回",
    )
    whitelist_user_count: int | None = Field(
        default=None,
        description="白名单中的号码数量（估算，可能存在少量误差）",
    )
    is_enable: Literal["on", "off"] | None = Field(
        default=None,
        description="策略是否启用：on=启用，off=关闭",
    )
    expire_at: str | None = Field(
        default=None,
        description="过期时间，RFC3339 格式",
    )
    created_at: str | None = Field(
        default=None,
        description="创建时间，RFC3339 格式",
    )
    updated_at: str | None = Field(
        default=None,
        description="最近更新时间，RFC3339 格式",
    )
    remark: str | None = Field(
        default=None,
        description="策略备注",
    )


class GetJoinApprovalStrategiesRequest(QQBotRequestModel):
    cursor: str | None = Field(
        default=None,
        description="分页游标，首次请求可不传或传空串",
    )
    limit: int | None = Field(
        default=None,
        le=50,
        description="单页数量，默认 20，最大 50",
    )


class GetJoinApprovalStrategiesResponse(QQBotBaseModel):
    strategies: list[JoinApprovalStrategy] | None = Field(
        default=None,
        description="生效中的策略列表，按创建时间倒序",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，空串表示已到末页",
    )


class CreateJoinApprovalStrategyRequest(QQBotRequestModel):
    group_openids: list[str] | None = Field(
        default=None,
        max_length=100,
        description="关联的群 openid 列表，与 group_ids 二选一必填，最多 100 个",
    )
    group_ids: list[str] | None = Field(
        default=None,
        max_length=100,
        description="关联的 QQ 群号列表（uint64），与 group_openids 二选一必填，最多 100 个",
    )
    is_enable: Literal["on", "off"] | None = Field(
        default=None,
        description="是否启用策略：on=启用，off=关闭，默认 on",
    )
    expire_at: str | None = Field(
        default=None,
        description="过期时间，RFC3339 格式；不传默认一年过期",
    )
    remark: str | None = Field(
        default=None,
        max_length=255,
        description="策略备注，最多 255 个汉字",
    )


class CreateJoinApprovalStrategyResponse(QQBotBaseModel):
    strategy_id: str = Field(
        ...,
        description="服务端生成的策略 ID",
    )
    is_enable: Literal["on", "off"] | None = Field(
        default=None,
        description="是否启用：on=启用，off=关闭",
    )
    expire_at: str | None = Field(
        default=None,
        description="过期时间，RFC3339 格式",
    )


class GroupAction(QQBotBaseModel):
    op: Literal["add", "del"] = Field(
        ...,
        description="操作类型：add=新增关联群，del=删除关联群",
    )
    group_openids: list[str] | None = Field(
        default=None,
        description="待操作的群 openid 列表，与 group_ids 互斥",
    )
    group_ids: list[str] | None = Field(
        default=None,
        description="待操作的 QQ 群号列表（uint64），与 group_openids 互斥",
    )


class UpdateJoinApprovalStrategyRequest(QQBotRequestModel):
    is_enable: Literal["on", "off"] | None = Field(
        default=None,
        description="是否启用策略：on=启用，off=关闭",
    )
    expire_at: str | None = Field(
        default=None,
        description="过期时间，RFC3339 格式",
    )
    group_action: GroupAction | None = Field(
        default=None,
        description="关联群增删操作，群标识形式须与创建时一致",
    )
    remark: str | None = Field(
        default=None,
        max_length=255,
        description="策略备注，最多 255 个汉字",
    )


class UpdateJoinApprovalStrategyResponse(QQBotBaseModel):
    is_enable: Literal["on", "off"] | None = Field(
        default=None,
        description="是否启用：on=启用，off=关闭",
    )
    expire_at: str | None = Field(
        default=None,
        description="过期时间，RFC3339 格式",
    )


class UpdateWhitelistUsersRequest(QQBotRequestModel):
    op: Literal["add", "del"] = Field(
        ...,
        description="操作类型：add=新增号码，del=删除号码",
    )
    whitelist_users: list[str] = Field(
        ...,
        max_length=10000,
        description="QQ 号码列表，单次最多 10000 个，使用字符串避免精度问题",
    )


class UpdateWhitelistUsersResponse(QQBotBaseModel):
    strategy_id: str | None = Field(
        default=None,
        description="策略 ID",
    )
    whitelist_user_count: int | None = Field(
        default=None,
        description="操作后策略当前白名单号码数（估算）",
    )
    updated_at: str | None = Field(
        default=None,
        description="策略更新时间，RFC3339 格式",
    )
