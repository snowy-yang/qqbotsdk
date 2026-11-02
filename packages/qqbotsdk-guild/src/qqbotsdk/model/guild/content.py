from typing import Literal

from pydantic import Field, RootModel

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel
from qqbotsdk.model.guild.member import Member


class RecommendChannel(QQBotBaseModel):
    channel_id: str | None = Field(
        default=None,
        description="推荐子频道 ID",
    )
    introduce: str | None = Field(
        default=None,
        description="推荐语",
    )


class CreateGuildAnnounceRequest(QQBotRequestModel):
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID，message_id 有值时必填",
    )
    message_id: str | None = Field(
        default=None,
        description="消息 ID，有值时创建消息类型的成员公告",
    )
    announces_type: Literal[0, 1] | None = Field(
        default=None,
        description="公告类别：0=成员公告，1=欢迎公告",
    )
    recommend_channels: list[RecommendChannel] | None = Field(
        default=None,
        description="推荐子频道列表，会一次全部替换；与消息类型公告互斥",
    )


class Announce(QQBotBaseModel):
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    message_id: str | None = Field(
        default=None,
        description="消息 ID",
    )
    announces_type: int | None = Field(
        default=None,
        description="公告类别：0=成员公告，1=欢迎公告",
    )
    recommend_channels: list[RecommendChannel] | None = Field(
        default=None,
        description="推荐子频道列表",
    )


class CreateGuildAnnounceResponse(Announce):
    pass


class PinsMessage(QQBotBaseModel):
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    message_ids: list[str] | None = Field(
        default=None,
        description="当前子频道内所有精华消息 ID",
    )


class GetChannelPinsResponse(PinsMessage):
    pass


class ScheduleInfo(QQBotBaseModel):
    name: str | None = Field(
        default=None,
        description="日程名称",
    )
    description: str | None = Field(
        default=None,
        description="日程描述",
    )
    start_timestamp: str | None = Field(
        default=None,
        description="开始时间，毫秒级时间戳字符串",
    )
    end_timestamp: str | None = Field(
        default=None,
        description="结束时间，毫秒级时间戳字符串",
    )
    jump_channel_id: str | None = Field(
        default=None,
        description="跳转子频道 ID",
    )
    remind_type: str | None = Field(
        default=None,
        description="提醒类型：0=不提醒，1=开始时提醒，2=开始前 5 分钟提醒，3=开始前 15 分钟提醒，4=开始前 30 分钟提醒，5=开始前 60 分钟提醒",
    )


class CreateChannelScheduleRequest(QQBotRequestModel):
    schedule: ScheduleInfo = Field(
        ...,
        description="日程对象，不需要带 id",
    )


class UpdateChannelScheduleRequest(QQBotRequestModel):
    schedule: ScheduleInfo = Field(
        ...,
        description="日程对象，不需要带 id",
    )


class Schedule(QQBotBaseModel):
    id: str | None = Field(
        default=None,
        description="日程 ID",
    )
    name: str | None = Field(
        default=None,
        description="日程名称",
    )
    description: str | None = Field(
        default=None,
        description="日程描述",
    )
    start_timestamp: str | None = Field(
        default=None,
        description="开始时间，毫秒级时间戳字符串",
    )
    end_timestamp: str | None = Field(
        default=None,
        description="结束时间，毫秒级时间戳字符串",
    )
    creator: Member | None = Field(
        default=None,
        description="创建者 member 信息",
    )
    jump_channel_id: str | None = Field(
        default=None,
        description="跳转子频道 ID",
    )
    remind_type: str | None = Field(
        default=None,
        description="提醒类型：0=不提醒，1=开始时提醒，2=开始前 5 分钟提醒，3=开始前 15 分钟提醒，4=开始前 30 分钟提醒，5=开始前 60 分钟提醒",
    )


class CreateChannelScheduleResponse(Schedule):
    pass


class UpdateChannelScheduleResponse(Schedule):
    pass


class GetChannelScheduleResponse(Schedule):
    pass


class GetChannelSchedulesRequest(QQBotRequestModel):
    since: int | None = Field(
        default=None,
        description="起始时间戳（毫秒）；不传返回当天日程",
    )


class GetChannelSchedulesResponse(RootModel[list[Schedule]]):
    pass


class AudioControlRequest(QQBotRequestModel):
    audio_url: str | None = Field(
        default=None,
        description="音频数据 URL，status=0 时传",
    )
    text: str | None = Field(
        default=None,
        description="状态文本，status=0 时传",
    )
    status: Literal[0, 1, 2, 3] = Field(
        ...,
        description="播放状态：0=开始，1=暂停，2=继续，3=停止",
    )


class ForumThreadInfo(QQBotBaseModel):
    thread_id: str | None = Field(
        default=None,
        description="主帖 ID",
    )
    title: str | None = Field(
        default=None,
        description="帖子标题",
    )
    content: str | None = Field(
        default=None,
        description="帖子内容；format=4 时为 RichText 的 JSON 字符串",
    )
    date_time: str | None = Field(
        default=None,
        description="发表时间，ISO8601 格式",
    )


class ForumThread(QQBotBaseModel):
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: str | None = Field(
        default=None,
        description="作者 ID",
    )
    thread_info: ForumThreadInfo | None = Field(
        default=None,
        description="主帖内容",
    )


class GetChannelThreadResponse(QQBotBaseModel):
    thread: ForumThread | None = Field(
        default=None,
        description="帖子详情对象",
    )


class GetChannelThreadsResponse(QQBotBaseModel):
    threads: list[ForumThread] | None = Field(
        default=None,
        description="帖子列表",
    )
    is_finish: int | None = Field(
        default=None,
        description="是否拉取完毕：0=否，1=是",
    )


class PutChannelThreadRequest(QQBotRequestModel):
    title: str = Field(
        ...,
        description="帖子标题",
    )
    content: str = Field(
        ...,
        description="帖子内容；format=4 时参照 RichText 结构",
    )
    format: Literal[1, 2, 3, 4] = Field(
        ...,
        description="内容格式：1=纯文本，2=HTML，3=Markdown，4=RichText JSON",
    )


class ForumTaskResponse(QQBotBaseModel):
    task_id: str | None = Field(
        default=None,
        description="异步任务 ID，结果经 FORUM_* 事件推送",
    )


class PutChannelThreadResponse(ForumTaskResponse):
    create_time: str | None = Field(
        default=None,
        description="发帖时间戳，单位：秒",
    )


class DeleteChannelThreadResponse(ForumTaskResponse):
    pass
