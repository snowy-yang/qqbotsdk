# 错误处理

三级错误全部继承 `QQBotError`，`except QQBotError` 能兜住一切。

| 异常 | 触发场景 | 关键属性 |
|---|---|---|
| `QQBotAPIError` | HTTP 4xx/5xx；HTTP 200 但 body 带非零 `err_code` / `code`；201/202 返回错误体 | `status`、`err_code`、`message`、`trace_id` |
| `QQBotAuthError` | 缺少凭证；换取 access_token 失败 | `message`、`code` |
| `QQBotGatewayError` | 网关致命关闭码（4001/4002/4010~4014/4914/4915）；网关响应缺少 `url` | `code`、`reason` |

```python
from qqbotsdk.errors import QQBotAPIError, QQBotAuthError, QQBotError

try:
    await send_group_messages(group_openid, request)
except QQBotAPIError as exc:
    print(exc.status, exc.err_code, exc.message, exc.trace_id)
except QQBotAuthError as exc:
    print("凭证问题:", exc.message)
except QQBotError:
    ...
```

`QQBotAPIError.__str__` 自带排障信息：

```
QQBotAPIError(status=200, err_code=40034005, message='回复消息msg_id已过期', trace_id=4a8a6156...)
```

## 无响应体接口

删除类接口返回 `204`、异步接口 `201/202`，旧实现会抛 `ContentTypeError`。现在统一返回空结果：

```python
async with session.delete(f"/v2/groups/{group_openid}/messages/{message_id}") as resp:
    data = await resp.json()  # 204 时得到 {}
```

## 429 自动重试

| 参数 | 默认值 | 说明 |
|---|---|---|
| `MAX_RETRIES` | 3 | 最多重试次数 |
| `RETRY_BASE_SECONDS` | 1.0 | 指数退避基数 |
| 等待策略 | — | 有 `Retry-After` 用它，否则 `base * 2**n` + 抖动 |
| 总等待上限 | 30 秒 | 超出即抛出 |

429 表示请求未被处理，因此 POST 也会重试。**非 429 一律不重试**。

```python
import qqbotsdk.api.core as core

core.MAX_RETRIES = 5  # 按需调整
```

## trace_id

优先取响应头 `X-Tps-trace-ID`，其次取 body 的 `trace_id`。提工单时直接贴这个 ID。

## 网关层

致命关闭码会终止客户端，原因通过 `last_error` 暴露：

```python
from qqbotsdk.errors import QQBotGatewayError

if isinstance(ws.last_error, QQBotGatewayError):
    print(ws.last_error.code, ws.last_error.reason)  # 4914 机器人已下架 / 4915 已封禁
```

上层 `Bot` 中，handler 的异常都会进 `on_error`（见 [app.md](app.md)），不会断连。

## 常见业务错误码

`err_code` 与 HTTP 状态码是两套东西：HTTP 200 也可能带非零 `err_code`。**不要用
`message` 判断失败**（平台随时调整文案），一律看 `err_code`。

SDK 提供了常量模块 `qqbotsdk.errors.codes`，不用再写魔法数字：

```python
from qqbotsdk.errors import QQBotAPIError, codes

try:
    await ctx.reply("...")
except QQBotAPIError as exc:
    if exc.err_code == codes.MSG_DEDUPLICATED:
        ...  # 40054005
    elif exc.err_code == codes.EVENT_NOT_REPLYABLE:
        ...  # 40034027
```

| 常量 | 错误码 | 含义 | 处理 |
|---|---|---|---|
| `MSG_TYPE_MISMATCH` | `22006` | 消息类型与内容不匹配 | 检查 `msg_type` 与内容字段（2.x 已自动推导） |
| `MSG_TYPE_INVALID` | `340069` | 消息类型无效 | 检查 `msg_type` 取值 |
| `MSG_CONTENT_INVALID` | `304061` | 消息内容无效 | 检查消息格式 |
| `MSG_ID_EXPIRED_ALT` | `304103` | 消息 ID 已过期，不能回复 | 被动回复窗口：群 5 分钟 / 单聊 60 分钟 |
| `MSG_ID_EXPIRED` | `40034005` | 回复消息 `msg_id` 已过期 | 同上 |
| `EVENT_ID_INVALID` | `40034025` | `event_id` 无效或越权 | 检查锚点是否取错 |
| `EVENT_ID_EXPIRED` | `40034026` | `event_id` 已过期 | 收到事件后尽快回复 |
| `EVENT_NOT_REPLYABLE` | `40034027` | 该事件不支持回复消息 | 例如 `GROUP_MEMBER_ADD` 只能发主动消息 |
| `MSG_DEDUPLICATED` | `40054005` | 消息被去重 | 递增 `msg_seq`（`ctx.reply()` 已自动处理） |
| `MSG_PASSIVE_LIMIT` | `40034128` | 被动回复时间/次数超限 | 群聊 5 次、单聊 4 次 |
| `MSG_ACTIVE_RATE_LIMITED` | `40034100` | 主动消息超频控 | 降低发送频率 |
| `BOT_NOT_IN_GROUP` | `40054003` | 机器人不是群成员 | 先把机器人拉进群 |
| `BOT_MUTED` | `40054002` | 机器人被禁言 | 等解禁 |
| `APP_PRIVILEGE_NOT_PASS` | `11253` | 应用未获得该接口权限 | 向平台申请 |
| `MEDIA_TRANSFER_FAILED` | `40034004` | 富媒体转存失败 | 可重试 |

另外 `MSG_LENGTH_EXCEEDED`（`40054007`）、`MSG_URL_NOT_ALLOWED`（`40054010`）、
`BOT_OFFLINE`（`40054016`）、`FILE_INFO_INVALID`（`304080`）与几条应用级错误码
也在这个模块里，完整列表见源码。

> `GROUP_FILE_NO_PERMISSION`（`40093005`）与 `QQ_STREAM_FETCH_FAILED`（`40093007`）
> 未收录在官方公共错误码表中，来自真实 bot 的调用日志，平台可能调整，**不要当成
> 稳定契约**。
