# API · 单聊

模块：`qqbotsdk.api.user`（核心包）。路径前缀 `/v2/users/{user_openid}/...`。`user_openid` 一律作第一个位置参数。

> 单聊与群聊的 openid **不通用**；群接口见 [group.md](group.md)。

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

**`SendUserMessagesRequest`**（全部可选，按 `msg_type` 取用）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `msg_type` | `Literal[0,2,6,7,8]` | 0=纯文本，2=Markdown，6=输入中状态，7=富媒体，8=图文卡片 |
| `content` | `str` | 文本内容；传 markdown 后须为空 |
| `markdown` | `MessageMarkdown` | msg_type=2 必填 |
| `keyboard` | `Keyboard` | 内嵌键盘 |
| `msg_id` | `str` | 被动回复的消息 ID，5 分钟内有效 |
| `event_id` | `str` | 被动回复的事件 ID，与 `msg_id` 二选一（支持 INTERACTION_CREATE / C2C_MSG_RECEIVE / FRIEND_ADD） |
| `msg_seq` | `int` | 回复序号，默认 1，相同 `msg_id`+`msg_seq` 重复发送会失败 |
| `media` | `MediaInfo` | msg_type=7 必填 |
| `message_reference` | `MessageReference` | 引用回复 |
| `is_wakeup` | `bool` | 互动召回消息，与 `msg_id`/`event_id` 互斥 |
| `input_notify` | `InputNotify` | msg_type=6 使用 |
| `card` | `MessageCard` | msg_type=8 必填 |

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
