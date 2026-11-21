# API · 单聊

模块：`qqbotsdk.api.user`（核心包）。路径前缀 `/v2/users/{user_openid}/...`。`user_openid` 一律作第一个位置参数。

> 单聊与群聊的 openid **不通用**；群接口见 [group.md](group.md)。

## 用户信息

```python
from qqbotsdk.api.user import get_user_info

info = await get_user_info(user_openid)
print(info.username, info.avatar, info.allow_proactive_msg)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_user_info(user_openid)` | `GET /v2/users/{user_openid}/info` | — → `GetUserInfoResponse` |

响应 `GetUserInfoResponse(union_openid, username, avatar, allow_proactive_msg)`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `union_openid` | `str` | 跨应用关联用户 openid，绑定了 3 方应用时有效 |
| `username` | `str` | 用户名 |
| `avatar` | `str` | 头像原图 URL |
| `allow_proactive_msg` | `bool` | 是否接收主动推送（发主动消息前先看这个） |

平台限制：10 QPS；与用户无好友关系时返回 `40184001`（`codes.USER_NO_FRIENDSHIP`）。

## 发送与撤回

```python
from qqbotsdk.api.user import send_user_messages, recall_user_messages
from qqbotsdk.model.user.messages import SendUserMessagesRequest

resp = await send_user_messages(
    user_openid,
    SendUserMessagesRequest(msg_type=0, content="hi"),
)
await recall_user_messages(user_openid, resp.id)  # 返回 None
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `send_user_messages(user_openid, payload)` | `POST /v2/users/{user_openid}/messages` | `SendUserMessagesRequest` → `SendUserMessagesResponse` |
| `recall_user_messages(user_openid, message_id)` | `DELETE /v2/users/{user_openid}/messages/{message_id}` | — → `None` |

响应 `SendUserMessagesResponse(id, timestamp, ext_info)`。

被动回复窗口：**60 分钟、4 次**（按 `msg_id` + `msg_seq` 计数）。

**`SendUserMessagesRequest`**（全部可选，按 `msg_type` 取用）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `msg_type` | `Literal[0,2,6,7,8]` | 0=纯文本，2=Markdown，6=输入中状态，7=富媒体，8=图文卡片 |
| `content` | `str` | 文本内容；传 markdown 后须为空 |
| `markdown` | `MessageMarkdown` | msg_type=2 必填 |
| `keyboard` | `Keyboard` | 内嵌键盘 |
| `msg_id` | `str` | 被动回复的消息 ID，来自 `C2C_MESSAGE_CREATE` 的 `d.id`；也可传群消息的 `d.id` 做「群消息私聊回复」（见下） |
| `event_id` | `str` | 被动回复的事件 ID，与 `msg_id` 二选一（支持 INTERACTION_CREATE / C2C_MSG_RECEIVE / FRIEND_ADD） |
| `msg_seq` | `int` | 回复序号，默认 1，相同 `msg_id`+`msg_seq` 重复发送会失败 |
| `media` | `MediaInfo` | msg_type=7 必填 |
| `message_reference` | `MessageReference` | 引用回复 |
| `is_wakeup` | `bool` | 互动召回消息，与 `msg_id`/`event_id` 互斥 |
| `input_notify` | `InputNotify` | msg_type=6 使用 |
| `card` | `MessageCard` | msg_type=8 必填 |

## 群消息私聊回复（2026-11-17 新增）

群消息事件（`GROUP_AT_MESSAGE_CREATE` / `GROUP_MESSAGE_CREATE`）的 `d.id` 也可以填进单聊请求的 `msg_id`，用来私聊回复这条群消息的发送者：

```python
from qqbotsdk.api.user import send_user_messages
from qqbotsdk.model.user.messages import SendUserMessagesRequest

await send_user_messages(
    user_openid,  # 必须是该群消息的发送者
    SendUserMessagesRequest(
        content="群里不方便说，私聊你", msg_id=group_event.id, msg_seq=1
    ),
)
```

约束：

- 要求该用户与机器人为好友关系，否则 `40054004 无好友关系`；`user_openid` 必须是这条群消息的发送者，否则 `40034024`。
- 有效时间与次数按**群消息**规则算：60 分钟；5 次，机器人开发者是该群群主/管理员时 50 次。
- 与群内回复**共用同一个 `msg_id` 的次数上限**：同一个锚点既在群里回又私聊回时两条一起占配额，`msg_seq` 也要一起排，否则会被 `40054005` 去重。
- 群消息事件体只给 `member_openid`，没有 `user_openid`。SDK 不做猜转换——要用这个能力，得自己拿到该发送者的 `user_openid`（例如他给你的单聊事件，或用 `union_openid` 关联）。

## 富媒体上传（三步）

流程与群聊一致（prepare → 分片 PUT → finish → upload 合并），仅路径换成单聊：

```python
import hashlib
from pathlib import Path

from qqbotsdk.api.core import session
from qqbotsdk.api.user import (
    prepare_user_upload,
    finish_user_upload_part,
    upload_user_file,
)
from qqbotsdk.model.sub.upload import UploadPrepareRequest, UploadPartFinishRequest
from qqbotsdk.model.user.messages import UploadUserFileRequest

p = Path("a.png")
prepared = await prepare_user_upload(
    user_openid,
    UploadPrepareRequest(
        file_type=1,
        file_size=str(p.stat().st_size),
        file_name=p.name,
        md5=m,
        sha1=s,
        md5_10m=m10,
    ),
)
data = p.read_bytes()
offset = 0
for part in sorted(prepared.parts or [], key=lambda x: x.index or 0):
    block = (
        int(part.block_size)
        if part.block_size
        else len(data) // len(prepared.parts or [1])
    )
    chunk = data[offset : offset + block]
    offset += len(chunk)
    async with session.put(part.presigned_url, data=chunk) as resp:
        await resp.read()
    await finish_user_upload_part(
        user_openid,
        UploadPartFinishRequest(
            upload_id=prepared.upload_id,
            part_index=part.index,
            block_size=str(len(chunk)),
            md5=hashlib.md5(chunk).hexdigest(),
        ),
    )
done = await upload_user_file(
    user_openid,
    UploadUserFileRequest(upload_id=prepared.upload_id, file_type=1, file_name=p.name),
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `prepare_user_upload(user_openid, payload)` | `POST /v2/users/{user_openid}/upload_prepare` | `UploadPrepareRequest` → `PrepareUserUploadResponse` |
| `finish_user_upload_part(user_openid, payload)` | `POST /v2/users/{user_openid}/upload_part_finish` | `UploadPartFinishRequest` → `None` |
| `upload_user_file(user_openid, payload)` | `POST /v2/users/{user_openid}/files` | `UploadUserFileRequest` → `UploadUserFileResponse` |

- **`UploadUserFileRequest`**（全部可选）：`file_type`(1图片/2视频/3语音/4文件)、`url`、`srv_send_msg`、`upload_id`、`file_name`、`file_data`（≤5M）。
- `UploadPrepareRequest` 字段同群聊（见 [group.md](group.md#富媒体上传三步)）。

## 流式消息

分片推送「生成中」文本，用于大模型逐字输出等场景。

```python
from qqbotsdk.api.user import send_user_stream_messages
from qqbotsdk.model.user.stream_messages import SendUserStreamMessagesRequest

# 第一片由服务端生成 stream_msg_id
r1 = await send_user_stream_messages(
    user_openid,
    SendUserStreamMessagesRequest(
        input_mode="append",
        input_state=1,
        index=0,
        content_type="markdown",
        content_raw="第一段",
    ),
)
# 后续分片携带上一片返回的 stream_msg_id，最后一片 input_state=10
await send_user_stream_messages(
    user_openid,
    SendUserStreamMessagesRequest(
        stream_msg_id=r1.id,
        input_state=10,
        index=1,
        content_type="markdown",
        content_raw="最后一段",
    ),
)
```

- `POST /v2/users/{user_openid}/stream_messages` → `SendUserStreamMessagesResponse`（`id`、`timestamp`、`ext_info`、`remain_msg_len`）
- **`SendUserStreamMessagesRequest`**（全部可选）：`input_mode`（`append`/`replace`）、`input_state`（`1`=生成中 / `10`=生成结束）、`index`（分片序号，从 0 递增）、`content_type`（`text`/`markdown`）、`content_raw`、`event_id`/`msg_id`（二选一）、`stream_msg_id`、`msg_seq`、`is_wakeup`。
