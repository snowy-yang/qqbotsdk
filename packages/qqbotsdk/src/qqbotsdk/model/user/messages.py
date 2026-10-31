from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.sub.messages import (
    InputNotify,
    Keyboard,
    MediaInfo,
    MessageCard,
    MessageExtInfo,
    MessageMarkdown,
    MessageReference,
)
from qqbotsdk.model.sub.upload import UploadPrepareResponse


class SendUserMessagesRequest(QQBotBaseModel):
    msg_type: Literal[0, 2, 6, 7, 8] | None = Field(
        None,
        description="消息类型：0=纯文本(content)，2=Markdown(markdown)，6=输入中状态(input_notify)，7=富媒体(media)，8=图文卡片(card)",
    )
    content: str | None = Field(
        None,
        description="文本内容。msg_type=0 时为全文；传了 markdown 后此字段必须为空",
    )
    markdown: MessageMarkdown | None = Field(
        None,
        description="Markdown 消息。msg_type=2 时必填",
    )
    keyboard: Keyboard | None = Field(
        None,
        description="内嵌键盘。短形式只传 id，长形式传 content.rows",
    )
    msg_id: str | None = Field(
        None,
        description="被动回复的消息 ID，5 分钟内有效",
    )
    event_id: str | None = Field(
        None,
        description="被动回复的事件 ID，与 msg_id 二选一",
    )
    msg_seq: int | None = Field(
        None,
        description="回复消息的序号，与 msg_id 联合使用，不填默认是 1",
    )
    media: MediaInfo | None = Field(
        None,
        description="富媒体消息。msg_type=7 时填写",
    )
    message_reference: MessageReference | None = Field(
        None,
        description="引用回复。填写后以引用形式展示",
    )
    is_wakeup: bool | None = Field(
        None,
        description="指明发送消息为互动召回消息，与 msg_id、event_id 互斥使用",
    )
    input_notify: InputNotify | None = Field(
        None,
        description="输入中状态，msg_type=6 时使用",
    )
    card: MessageCard | None = Field(
        None,
        description="图文卡片消息。msg_type=8 时必填",
    )


class SendUserMessagesResponse(QQBotBaseModel):
    id: str = Field(
        ...,
        description="消息 ID，可用于后续撤回",
    )
    timestamp: str = Field(
        ...,
        description="发送时间，RFC3339 东八区",
    )
    ext_info: MessageExtInfo | None = Field(
        None,
        description="扩展信息",
    )


class UploadUserFileRequest(QQBotBaseModel):
    file_type: int | None = Field(
        None,
        description="媒体类型：1=图片，2=视频，3=语音，4=文件",
    )
    url: str | None = Field(
        None,
        description="媒体资源 URL，需以 http 开头；分片上传合并时可为空",
    )
    srv_send_msg: bool | None = Field(
        None,
        description="true=直接发送消息并占用主动消息频次；false=仅返回 file_info",
    )
    upload_id: str | None = Field(
        None,
        description="分片上传任务 ID；传入后走分片上传合并路径，url 可为空",
    )
    file_name: str | None = Field(
        None,
        description="文件名，分片上传或二进制上传时必填",
    )
    file_data: str | None = Field(
        None,
        description="直接上传的二进制数据，大小不能超过 5M",
    )


class UploadUserFileResponse(QQBotBaseModel):
    file_uuid: str | None = Field(
        None,
        description="文件唯一 ID",
    )
    file_info: str | None = Field(
        None,
        description="文件信息，用于发送消息接口的 media.file_info",
    )
    ttl: int | None = Field(
        None,
        description="file_info 有效期（秒）；0 表示可长期使用",
    )
    id: str | None = Field(
        None,
        description="发送消息的唯一 ID，仅 srv_send_msg=true 时返回",
    )
    raw_url: str | None = Field(
        None,
        description="文件下载链接，仅分片上传合并且 file_type 为图片/视频/语音时返回",
    )


class PrepareUserUploadResponse(UploadPrepareResponse):
    pass
