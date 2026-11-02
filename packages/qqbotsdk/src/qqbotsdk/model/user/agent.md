# agent.md — qqbotsdk/model/user（单聊模型）

适用范围：`packages/qqbotsdk/src/qqbotsdk/model/user/**`（`messages.py`、`stream_messages.py`）。

## MUST（必须做）

- MUST 区分单聊专有字段，不要与群聊模型合并：
  - `msg_type` 为 `Literal[0, 2, 6, 7, 8]`（6 = 输入中状态）；
  - `is_wakeup`（互动召回消息，与 `msg_id`/`event_id` 互斥）；
  - `input_notify`（`InputNotify`，`msg_type=6` 时使用）。
- MUST 保留流式消息的语义字段：`input_mode`（`append`/`replace`）、`input_state`（1=生成中，10=生成结束）、`index`、`content_type`、`content_raw`、`stream_msg_id`、`msg_seq`、`is_wakeup`。
- MUST 让响应模型给出流式专有字段：`SendUserStreamMessagesResponse.remain_msg_len`。
- MUST 让文件上传模型（`UploadUserFileRequest/Response`、`PrepareUserUploadResponse`）与群聊版本保持字段一致，仅类名不同。

## SHOULD（应当做）

- SHOULD 在 `description` 里写明被动回复窗口（单聊 60 分钟、4 次）这类硬约束，便于调用方排查。
- SHOULD 复用 `qqbotsdk-base` 的 `MessageMarkdown`、`Keyboard`、`MediaInfo`、`MessageReference`、`MessageCard`。

## MUST NOT（禁止做）

- MUST NOT 把 `user_openid` 写进请求体模型（路径参数）。
- MUST NOT 给单聊模型加群聊专有字段（`group_openid`、`member_openid`）。
- MUST NOT 用 `Literal` 收窄 `msg_type` 之外可能扩展的字段（`file_type` 用 `Literal[1,2,3,4]` 是可以的，它由文档定义且封闭）。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\model\user
.venv\Scripts\pyright.exe
```
