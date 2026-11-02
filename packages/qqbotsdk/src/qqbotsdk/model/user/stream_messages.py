from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel
from qqbotsdk.model.sub.messages import (
    MessageExtInfo,
)


class SendUserStreamMessagesRequest(QQBotRequestModel):
    input_mode: Literal["append", "replace"] | None = Field(
        "append",
        description=(
            "输入模式。"
            "append（默认）：ContentRaw 拼接到 Pending；"
            "replace：ContentRaw 为当前全量正文，须以上游已下发前缀 SentContent 开头，"
            "合并后 Pending 仅存未下发后缀。"
        ),
    )
    input_state: Literal[1, 10] | None = Field(
        default=None,
        description="输入状态。1=生成中，10=生成结束",
    )
    index: int | None = Field(
        default=None,
        description="分片序号，从 0 递增",
    )
    content_type: Literal["text", "markdown"] | None = Field(
        default=None,
        description="内容格式类型。text=文本消息，markdown=MarkDown 消息",
    )
    content_raw: str | None = Field(
        default=None,
        description="Markdown 格式的文本内容",
    )
    event_id: str | None = Field(
        default=None,
        description="被动回复事件ID（与 msg_id 二选一）",
    )
    msg_id: str | None = Field(
        default=None,
        description="被动回复消息ID（与 event_id 二选一）",
    )
    stream_msg_id: str | None = Field(
        default=None,
        description="流式消息ID。第一条由服务端生成并返回，后续分片需携带上一分片返回的 id",
    )
    msg_seq: int | None = Field(
        default=None,
        description="消息序号，用于去重",
    )
    is_wakeup: bool | None = Field(
        default=None,
        description="是否为召回消息。true 时不校验 msg_id/event_id 有效期",
    )


class SendUserStreamMessagesResponse(QQBotBaseModel):
    id: str = Field(
        ...,
        description="消息ID。首条返回 stream_msg_id，用于后续分片",
    )
    timestamp: str = Field(
        ...,
        description="消息发送时间，RFC3339 格式",
    )
    ext_info: MessageExtInfo | None = Field(
        default=None,
        description="扩展信息",
    )
    remain_msg_len: int | None = Field(
        default=None,
        description="流式消息剩余长度（字符数）",
    )
