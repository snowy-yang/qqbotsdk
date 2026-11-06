"""OpenAPI 业务错误码常量.

``QQBotAPIError.err_code`` 是**业务错误码**, 与 HTTP 状态码分开: HTTP 200 时
也可能带非零 ``err_code``. 用这里的常量替代魔法数字::

    from qqbotsdk.errors import QQBotAPIError, codes

    try:
        await ctx.reply("...")
    except QQBotAPIError as exc:
        if exc.err_code == codes.MSG_MSG_ID_EXPIRED:
            ...

命名规范: 前缀是错误码所属的域(``MSG_`` 消息、``APP_`` 应用权限、
``FILE_`` 文件), 名字取官方错误表里英文标识的大写形式; 官方只给了中文描述的,
按描述意译.

来源: 官方 [API 调用指南 · 公共错误码] 与各接口页的「错误码」表. 标注为
「实践观察」的几条未收录在官方公共错误表中, 来自真实 bot 的调用日志, 平台可能
调整, 不要把它们当成稳定契约.
"""

from typing import Final

# ---------------------------------------------------------------- 消息收发

MSG_DEDUPLICATED: Final = 40054005
"""相同 msg_id + msg_seq 重复发送被去重. 递增 msg_seq 即可."""

MSG_ID_EXPIRED: Final = 40034005
"""回复消息的 msg_id 已过期, 请在收到消息后尽快回复."""

EVENT_ID_INVALID: Final = 40034025
"""请求参数 event_id 无效或越权."""

EVENT_ID_EXPIRED: Final = 40034026
"""请求参数 event_id 已过期, 请在收到事件后尽快回复."""

EVENT_NOT_REPLYABLE: Final = 40034027
"""该事件不支持回复消息. 例如 GROUP_MEMBER_ADD 只能发主动消息."""

MSG_TYPE_MISMATCH: Final = 22006
"""消息类型与内容不匹配(例如 msg_type=2 却只传了 content)."""

MSG_TYPE_INVALID: Final = 340069
"""消息类型无效, 检查 msg_type 取值."""

MSG_CONTENT_INVALID: Final = 304061
"""消息内容无效, 检查消息格式."""

MSG_LENGTH_EXCEEDED: Final = 40054007
"""消息长度超限."""

MSG_URL_NOT_ALLOWED: Final = 40054010
"""不允许发送 URL."""

MSG_PASSIVE_LIMIT: Final = 40034128
"""被动回复时间或次数超限(群聊 5 次 / 单聊 4 次)."""

MSG_ACTIVE_RATE_LIMITED: Final = 40034100
"""主动消息发送超过频控限制."""

BOT_NOT_IN_GROUP: Final = 40054003
"""机器人不是群成员."""

BOT_MUTED: Final = 40054002
"""机器人被禁言, 等解禁后再发送."""

BOT_OFFLINE: Final = 40054016
"""机器人已下线, 检查网关连接状态."""

MEDIA_TRANSFER_FAILED: Final = 40034004
"""富媒体信息转存失败, 可重试."""

FILE_INFO_INVALID: Final = 304080
"""文件信息无效, 检查 file_info 格式."""

MSG_ID_EXPIRED_ALT: Final = 304103
"""消息 ID 已过期, 不能回复."""

# ---------------------------------------------------------------- 应用与权限

APP_PRIVILEGE_NOT_PASS: Final = 11253
"""应用权限不通过: 该机器人未获得调用该接口的权限, 需要向平台申请."""

APP_PRIVILEGE_CHECK_FAILED: Final = 11252
"""检查应用权限失败(系统错误), 通常重试一次即可."""

APP_INTERFACE_FORBIDDEN: Final = 11254
"""应用接口被封禁: 有该接口权限但被封禁."""

BOT_BANNED: Final = 11265
"""机器人已经被封禁."""

# ---------------------------------------------------------------- 实践观察
# 以下未收录在官方公共错误码表中, 来自真实 bot 的调用日志, 平台可能调整.

GROUP_FILE_NO_PERMISSION: Final = 40093005
"""群文件无权限(实践观察). 常见于机器人缺少群文件读写权限时."""

QQ_STREAM_FETCH_FAILED: Final = 40093007
"""QQ 抓流失败(实践观察). 常见于语音 / 视频链接平台侧拉取失败."""

__all__ = [
    "APP_INTERFACE_FORBIDDEN",
    "APP_PRIVILEGE_CHECK_FAILED",
    "APP_PRIVILEGE_NOT_PASS",
    "BOT_BANNED",
    "BOT_MUTED",
    "BOT_NOT_IN_GROUP",
    "BOT_OFFLINE",
    "EVENT_ID_EXPIRED",
    "EVENT_ID_INVALID",
    "EVENT_NOT_REPLYABLE",
    "FILE_INFO_INVALID",
    "GROUP_FILE_NO_PERMISSION",
    "MEDIA_TRANSFER_FAILED",
    "MSG_ACTIVE_RATE_LIMITED",
    "MSG_CONTENT_INVALID",
    "MSG_DEDUPLICATED",
    "MSG_ID_EXPIRED",
    "MSG_ID_EXPIRED_ALT",
    "MSG_LENGTH_EXCEEDED",
    "MSG_PASSIVE_LIMIT",
    "MSG_TYPE_INVALID",
    "MSG_TYPE_MISMATCH",
    "MSG_URL_NOT_ALLOWED",
    "QQ_STREAM_FETCH_FAILED",
]
