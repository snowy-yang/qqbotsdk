# agent.md — qqbotsdk/model/group（群聊与群管理模型）

适用范围：`packages/qqbotsdk/src/qqbotsdk/model/group/**`（`messages.py`、`member.py`、`mute.py`、`blacklist.py`、`join_request.py`、`strategy.py`）。

## MUST（必须做）

- MUST 让群域模型与 `api/group/` 同名对应（`mute.py` ↔ `api/group/mute.py`）。
- MUST 对操作类型字段用 `Literal` 并带中文取值说明，例如：
  - `UpdateGroupBlacklistRequest.op` → `Literal["add", "del"]`
  - `ReviewGroupJoinRequest.op` → `Literal["approve", "decline"]`
  - `SetMemberMuteState.op` → `Literal["add", "update", "del"]`
  - `GlobalMuteRule.mode` → `Literal["none", "always", "schedule"]`
- MUST 给数量上限加约束：`member_openids` `max_length=20`、`group_openids` `max_length=100`、`whitelist_users` `max_length=10000`。
- MUST 给分页参数加 `le`（黑名单 `le=100`、入群申请与审批策略 `le=50`）。
- MUST 复用 `qqbotsdk-base` 的共享子模型（消息、键盘、Markdown、卡片、上传）。

## SHOULD（应当做）

- SHOULD 让条件字段的 `description` 写清「何时才有值」（例如 `msg_id`/`event_id` 二选一、`media` 仅 `msg_type=7`）。
- SHOULD 让 `SendGroupMessagesRequest.msg_type` 保持 `Literal[0, 2, 7, 8]`（群聊没有输入中状态 6）。

## MUST NOT（禁止做）

- MUST NOT 把 `group_openid` 写进请求体模型（它是路径参数）。
- MUST NOT 复用单聊模型：`msg_type` 取值集合、`is_wakeup`、`input_notify` 都是单聊独有。
- MUST NOT 对可能扩容的字段用 `Literal`（如事件的 `message_type`），否则真实推送会被误拒。
- MUST NOT 建模官方标注【已废弃】的字段。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\model\group
.venv\Scripts\pyright.exe
```
