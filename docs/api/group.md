# API · 群聊与群管理

模块前缀：`qqbotsdk.api.group.*`（核心包）。`group_openid` 一律作第一个位置参数，路径前缀 `/v2/groups/{group_openid}/...`。区分 `group_openid`（群）与 `member_openid`（群内成员）。

| 文件 | 域 | 接口 |
|---|---|---|
| `group.messages` | 群消息与富媒体 | `send_group_messages` / `recall_group_messages` / `upload_group_file` / `prepare_group_upload` / `finish_group_upload_part` |
| `group.manage` | 群信息与成员 | `get_group_info` / `get_group_members` / `get_group_member` / `get_group_bot_state` / `remove_group_members` |
| `group.mute` | 群禁言 | `get_group_mute_state` / `set_group_mute_state` |
| `group.blacklist` | 群黑名单 | `get_group_blacklist` / `update_group_blacklist` |
| `group.join_request` | 入群审批 | `get_group_join_requests` / `review_group_join_request` |
| `group.strategy` | 自动审批策略 | `get_join_approval_strategies` 等 6 个 |

---

## 群消息 group.messages

### send_group_messages

```python
from qqbotsdk.api.group.messages import send_group_messages
from qqbotsdk.model.group.messages import SendGroupMessagesRequest

resp = await send_group_messages(
    group_openid,
    SendGroupMessagesRequest(msg_type=0, content="hi"),
)
print(resp.id, resp.timestamp)
```

- `POST /v2/groups/{group_openid}/messages` → `SendGroupMessagesResponse`
- 响应 `SendGroupMessagesResponse(id, timestamp, ext_info)`。

请求 `SendGroupMessagesRequest`（全部可选，按 `msg_type` 取用）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `msg_type` | `Literal[0,2,7,8]` | 0=纯文本(content)，2=Markdown(markdown)，7=富媒体(media)，8=图文卡片(card) |
| `content` | `str` | 文本内容；msg_type=0 为全文；传 markdown 后须为空 |
| `markdown` | `MessageMarkdown` | msg_type=2 必填 |
| `keyboard` | `Keyboard` | 内嵌键盘；短形式只传 id，长形式传 content.rows |
| `msg_id` | `str` | 被动回复的消息 ID，取事件 `d.id`，5 分钟内有效 |
| `event_id` | `str` | 被动回复的事件 ID，与 `msg_id` 二选一 |
| `msg_seq` | `int` | 回复序号，与 `msg_id` 联合使用，默认 1 |
| `media` | `MediaInfo` | msg_type=7，`file_info` 来自富媒体上传接口 |
| `message_reference` | `MessageReference` | 引用回复 |
| `card` | `MessageCard` | msg_type=8 必填 |

### recall_group_messages

```python
from qqbotsdk.api.group.messages import recall_group_messages

await recall_group_messages(group_openid, message_id)  # 返回 None
```

- `DELETE /v2/groups/{group_openid}/messages/{message_id}` → `None`

### 富媒体上传（三步）

```python
import hashlib
from pathlib import Path

from qqbotsdk.api.core import session
from qqbotsdk.api.group.messages import (
    prepare_group_upload,
    finish_group_upload_part,
    upload_group_file,
)
from qqbotsdk.model.sub.upload import UploadPrepareRequest, UploadPartFinishRequest
from qqbotsdk.model.group.messages import UploadGroupFileRequest

file = Path("a.png")
prepared = await prepare_group_upload(
    group_openid,
    UploadPrepareRequest(
        file_type=1,
        file_size=str(file.stat().st_size),
        file_name=file.name,
        md5=md5_hex,
        sha1=sha1_hex,
        md5_10m=md5_10m_hex,
    ),
)

# 按 parts（顶层字段，按 index 排序）逐片 PUT 到预签名 URL，每片传完要通知服务端
data = file.read_bytes()
offset = 0
for part in sorted(prepared.parts or [], key=lambda p: p.index or 0):
    block = (
        int(part.block_size)
        if part.block_size
        else len(data) // len(prepared.parts or [1])
    )
    chunk = data[offset : offset + block]
    offset += len(chunk)
    async with session.put(part.presigned_url, data=chunk) as resp:
        await resp.read()
    await finish_group_upload_part(
        group_openid,
        UploadPartFinishRequest(
            upload_id=prepared.upload_id,
            part_index=part.index,
            block_size=str(len(chunk)),
            md5=hashlib.md5(chunk).hexdigest(),
        ),
    )

# 合并拿 file_info
done = await upload_group_file(
    group_openid,
    UploadGroupFileRequest(
        upload_id=prepared.upload_id, file_type=1, file_name=file.name
    ),
)
# 之后以 msg_type=7 + MediaInfo(file_info=done.file_info) 发送
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `prepare_group_upload(group_openid, payload)` | `POST /v2/groups/{group_openid}/upload_prepare` | `UploadPrepareRequest` → `PrepareGroupUploadResponse` |
| `finish_group_upload_part(group_openid, payload)` | `POST /v2/groups/{group_openid}/upload_part_finish` | `UploadPartFinishRequest` → `None` |
| `upload_group_file(group_openid, payload)` | `POST /v2/groups/{group_openid}/files` | `UploadGroupFileRequest` → `UploadGroupFileResponse` |

**`UploadPrepareRequest`**（全部必填）：`file_type`（1=图片,2=视频,3=语音,4=文件）、`file_size`（字符串字节数）、`file_name`、`md5`、`sha1`、`md5_10m`（前 10002432 字节的 MD5）。

`PrepareGroupUploadResponse`：`upload_id`、`block_size`、`parts: list[UploadPart]`（`index`/`presigned_url`/`block_size`）、`upload_config`（`concurrency`/`retry_timeout`/`retry_delay`）。

**`UploadGroupFileRequest`**（全部可选）：`file_type`(1-4)、`url`（http 开头，平台下载转存）、`srv_send_msg`（true=直接发消息占频次）、`upload_id`（分片合并时传）、`file_name`、`file_data`（≤5M 二进制）。

`UploadGroupFileResponse`：`file_uuid`、`file_info`、`ttl`、`id`、`raw_url`。

---

## 群信息与成员 group.manage

```python
from qqbotsdk.api.group.manage import (
    get_group_info,
    get_group_members,
    get_group_member,
    get_group_bot_state,
    remove_group_members,
)
from qqbotsdk.model.group.member import (
    GetGroupMembersRequest,
    RemoveGroupMembersRequest,
)
```

| 接口 | 路由 | 请求 / 响应 | 说明 |
|---|---|---|---|
| `get_group_info(group_openid)` | `GET /v2/groups/{group_openid}/info` | — → `GetGroupInfoResponse` | 群名称、标签、成员数等 |
| `get_group_members(group_openid, payload)` | `GET /v2/groups/{group_openid}/members` | `GetGroupMembersRequest` → `GetGroupMembersResponse` | 分页成员列表 |
| `get_group_member(group_openid, member_openid)` | `GET /v2/groups/{group_openid}/members/{member_openid}` | — → `GetGroupMemberResponse` | 单个成员 |
| `get_group_bot_state(group_openid)` | `GET /v2/groups/{group_openid}/bot_state` | — → `GetGroupBotStateResponse` | 机器人入群状态 |
| `remove_group_members(group_openid, payload)` | `POST /v2/groups/{group_openid}/batch_remove_members` | `RemoveGroupMembersRequest` → `RemoveGroupMembersResponse` | 批量移出成员 |

- **`GetGroupMembersRequest`**：`cursor`（可选，翻页传上一页 `next_cursor`）。
- `GetGroupMembersResponse`：`members: list[GroupMember]`、`next_cursor`。`GroupMember` 含 `member_openid`、`username`、`member_role`（`member`/`owner`/`admin`）、`bot`、`joined_at`、`union_openid`。
- `GetGroupInfoResponse`：`group_openid`、`group_name`、`group_finger_memo`、`group_class_text`、`group_tags`、`group_member_num`。
- `GetGroupBotStateResponse`：`member_openid`、`joined_at`、`allow_proactive_msg`、`recv_msg_setting`、`member_role`（`member`/`owner`/`admin`）。
- `RemoveGroupMembersResponse`：`remove_members_result: str | None`、`add_to_member_blacklist_fail_openids: list[str] | None`。
- **`RemoveGroupMembersRequest`**：`member_openids: list[str]`（必填，≤20）、`add_to_member_blacklist`（可选，默认 false）。

---

## 群禁言 group.mute

```python
from qqbotsdk.api.group.mute import get_group_mute_state, set_group_mute_state
from qqbotsdk.model.group.mute import SetGroupMuteStateRequest
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_group_mute_state(group_openid)` | `GET /v2/groups/{group_openid}/restrict_chat_setting` | — → `GetGroupMuteStateResponse` |
| `set_group_mute_state(group_openid, payload)` | `POST /v2/groups/{group_openid}/restrict_chat_setting` | `SetGroupMuteStateRequest` → `None` |

- **`SetGroupMuteStateRequest`**：`members: list[SetMemberMuteState]`（可选），每项通过 `op` 增/改/删，单次 ≤20。

---

## 群黑名单 group.blacklist

```python
from qqbotsdk.api.group.blacklist import get_group_blacklist, update_group_blacklist
from qqbotsdk.model.group.blacklist import (
    GetGroupBlacklistRequest,
    UpdateGroupBlacklistRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_group_blacklist(group_openid, payload)` | `GET /v2/groups/{group_openid}/member_blacklist` | `GetGroupBlacklistRequest` → `GetGroupBlacklistResponse` |
| `update_group_blacklist(group_openid, payload)` | `POST /v2/groups/{group_openid}/member_blacklist` | `UpdateGroupBlacklistRequest` → `UpdateGroupBlacklistResponse` |

- **`GetGroupBlacklistRequest`**：`cursor`（可选）、`limit`（可选，默认 20，最大 100）。
- `GetGroupBlacklistResponse`：`users: list[BlacklistUser]`、`next_cursor`。
- **`UpdateGroupBlacklistRequest`**：`op`（必填，`add`/`del`）、`member_openids: list[str]`（必填，≤20）。

---

## 入群审批 group.join_request

```python
from qqbotsdk.api.group.join_request import (
    get_group_join_requests,
    review_group_join_request,
)
from qqbotsdk.model.group.join_request import (
    GetGroupJoinRequestsRequest,
    ReviewGroupJoinRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_group_join_requests(group_openid, payload)` | `GET /v2/groups/{group_openid}/join_request_list` | `GetGroupJoinRequestsRequest` → `GetGroupJoinRequestsResponse` |
| `review_group_join_request(group_openid, member_openid, payload)` | `POST /v2/groups/{group_openid}/approval_join_request/{member_openid}` | `ReviewGroupJoinRequest` → `None` |

- **`GetGroupJoinRequestsRequest`**：`cursor`、`limit`（默认 20，最大 50）。
- `GetGroupJoinRequestsResponse`：`join_requests: list[JoinRequest]`、`next_cursor`。`JoinRequest` 含 `join_request_id`、`member_openid`、`username`、`apply_at`、`apply_source`、`invited_by`、`bot`、`risk_tips`、`verify_info` 等。
- **`ReviewGroupJoinRequest`**：`op`（必填，`approve`/`decline`）、`join_request_id`、`reject_reason`（decline 时可用）、`add_to_member_blacklist`（decline 时可用）。

> 更省事的封装见 [app.md](../app.md) 的 `ctx.api.approve_join_request()` / `decline_join_request()`。

---

## 自动审批策略 group.strategy

```python
from qqbotsdk.api.group.strategy import (
    get_join_approval_strategies,
    create_join_approval_strategy,
    update_join_approval_strategy,
    delete_join_approval_strategy,
    execute_join_approval_strategy,
    update_join_approval_strategy_whitelist,
)
from qqbotsdk.model.group.strategy import (
    GetJoinApprovalStrategiesRequest,
    CreateJoinApprovalStrategyRequest,
    UpdateJoinApprovalStrategyRequest,
    UpdateWhitelistUsersRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_join_approval_strategies(payload)` | `GET /v2/groups/join_approval_strategy` | `GetJoinApprovalStrategiesRequest` → `GetJoinApprovalStrategiesResponse` |
| `create_join_approval_strategy(payload)` | `POST /v2/groups/join_approval_strategy` | `CreateJoinApprovalStrategyRequest` → `CreateJoinApprovalStrategyResponse` |
| `update_join_approval_strategy(strategy_id, payload)` | `PATCH /v2/groups/join_approval_strategy/{strategy_id}` | `UpdateJoinApprovalStrategyRequest` → `UpdateJoinApprovalStrategyResponse` |
| `delete_join_approval_strategy(strategy_id)` | `DELETE /v2/groups/join_approval_strategy/{strategy_id}` | — → `None` |
| `execute_join_approval_strategy(strategy_id)` | `POST /v2/groups/join_approval_strategy/{strategy_id}/execute` | — → `None` |
| `update_join_approval_strategy_whitelist(strategy_id, payload)` | `POST /v2/groups/join_approval_strategy/{strategy_id}/whitelist_users` | `UpdateWhitelistUsersRequest` → `UpdateWhitelistUsersResponse` |

> 注意：这一组接口**不需要 `group_openid`**（策略按群 openid/群号在请求体里关联），因此路径里没有群 ID。

- **`GetJoinApprovalStrategiesRequest`**：`cursor`、`limit`（默认 20，最大 50）。
- **`CreateJoinApprovalStrategyRequest`**：`group_openids` / `group_ids`（二选一必填，≤100）、`is_enable`（`on`/`off`，默认 on）、`expire_at`（RFC3339，默认一年）、`remark`（≤255 汉字）。
- **`UpdateJoinApprovalStrategyRequest`**：`is_enable`、`expire_at`、`group_action`（`GroupAction`）、`remark`。
- **`UpdateWhitelistUsersRequest`**：`op`（必填，`add`/`del`）、`whitelist_users: list[str]`（必填，≤10000，用字符串避免精度问题）。
