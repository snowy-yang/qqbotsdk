from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class ReviewQA(QQBotBaseModel):
    question: str | None = Field(
        None,
        description="管理员设置的问题",
    )
    answer: str | None = Field(
        None,
        description="申请人填写的答案",
    )


class VerifyInfo(QQBotBaseModel):
    method: str | None = Field(
        None,
        description="入群验证方式：verify_message / admin_review_qa",
    )
    verify_message: str | None = Field(
        None,
        description="验证消息内容",
    )
    review_qa_list: list[ReviewQA] | None = Field(
        None,
        description="问答列表",
    )


class JoinRequest(QQBotBaseModel):
    join_request_id: str | None = Field(
        None,
        description="申请 ID，审批时需回传",
    )
    risk_tips: str | None = Field(
        None,
        description="安全提示语",
    )
    union_openid: str | None = Field(
        None,
        description="跨应用统一标识（如有）",
    )
    member_openid: str | None = Field(
        None,
        description="申请人 openid",
    )
    username: str | None = Field(
        None,
        description="申请人昵称",
    )
    apply_at: str | None = Field(
        None,
        description="申请时间戳，RFC3339 格式",
    )
    apply_source: str | None = Field(
        None,
        description="申请来源：self_apply=主动申请，invited=被邀请",
    )
    invited_by: str | None = Field(
        None,
        description="邀请人 openid，apply_source=invited 时有效",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人账号",
    )
    verify_info: VerifyInfo | None = Field(
        None,
        description="用户入群验证方式",
    )


class GetGroupJoinRequestsRequest(QQBotBaseModel):
    cursor: str | None = Field(
        None,
        description="分页游标，首次不传",
    )
    limit: int | None = Field(
        None,
        description="单页数量，默认 20，最大 50",
    )


class GetGroupJoinRequestsResponse(QQBotBaseModel):
    join_requests: list[JoinRequest] | None = Field(
        None,
        alias="list",
        description="入群申请列表",
    )
    next_cursor: str | None = Field(
        None,
        description="下一页游标，空串表示已到末页",
    )


class ReviewGroupJoinRequest(QQBotBaseModel):
    op: str = Field(
        ...,
        description="审批动作：approve=通过，decline=拒绝",
    )
    join_request_id: str | None = Field(
        None,
        description="申请 ID",
    )
    reject_reason: str | None = Field(
        None,
        description="拒绝理由，op=decline 时可填",
    )
    add_to_member_blacklist: bool | None = Field(
        None,
        description="是否同时加入群黑名单，op=decline 时可填",
    )
