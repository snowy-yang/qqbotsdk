from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class ReviewQA(QQBotBaseModel):
    question: str | None = Field(
        default=None,
        description="管理员设置的问题",
    )
    answer: str | None = Field(
        default=None,
        description="申请人填写的答案",
    )


class VerifyInfo(QQBotBaseModel):
    method: Literal["verify_message", "admin_review_qa"] | None = Field(
        default=None,
        description="入群验证方式：verify_message / admin_review_qa",
    )
    verify_message: str | None = Field(
        default=None,
        description="验证消息内容，仅 method=verify_message 时可能携带",
    )
    review_qa_list: list[ReviewQA] | None = Field(
        default=None,
        description="问答列表，仅 method=admin_review_qa 时可能携带",
    )


class JoinRequest(QQBotRequestModel):
    join_request_id: str | None = Field(
        default=None,
        description="申请 ID，审批时需回传",
    )
    risk_tips: str | None = Field(
        default=None,
        description="安全提示语，可疑消息返回 warning_tips，普通消息命中 sec_risk_rules 时返回 top_tips",
    )
    union_openid: str | None = Field(
        default=None,
        description="用户在应用/开放平台下的统一标识（如有）",
    )
    member_openid: str | None = Field(
        default=None,
        description="申请人 openid",
    )
    username: str | None = Field(
        default=None,
        description="申请人昵称",
    )
    apply_at: str | None = Field(
        default=None,
        description="申请时间戳，RFC3339 格式",
    )
    apply_source: Literal["self_apply", "invited"] | None = Field(
        default=None,
        description="申请来源：self_apply=主动申请，invited=被邀请",
    )
    invited_by: str | None = Field(
        default=None,
        description="邀请人 openid，apply_source=invited 时有效",
    )
    bot: bool | None = Field(
        default=None,
        description="是否为机器人账号",
    )
    verify_info: VerifyInfo | None = Field(
        default=None,
        description="用户入群验证方式",
    )


class GetGroupJoinRequestsRequest(QQBotRequestModel):
    cursor: str | None = Field(
        default=None,
        description="分页游标，首次请求可不传或传空串",
    )
    limit: int | None = Field(
        default=None,
        le=50,
        description="单页数量，默认 20，最大 50",
    )


class GetGroupJoinRequestsResponse(QQBotBaseModel):
    join_requests: list[JoinRequest] | None = Field(
        default=None,
        alias="list",
        description="入群申请列表",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，空串表示已到末页",
    )


class ReviewGroupJoinRequest(QQBotRequestModel):
    op: Literal["approve", "decline"] = Field(
        ...,
        description="审批动作：approve=通过，decline=拒绝",
    )
    join_request_id: str | None = Field(
        default=None,
        description="申请 ID，审批时需回传",
    )
    reject_reason: str | None = Field(
        default=None,
        description="拒绝理由，op=decline 时可填",
    )
    add_to_member_blacklist: bool | None = Field(
        default=None,
        description="是否同时加入群黑名单，默认 false，op=decline 时可填",
    )
