# API 层（薄映射）

`qqbotsdk.api` 与 `qqbotsdk.model` 是一对一的协议映射：**一个接口一个函数，一个请求体一个模型**。整层没有业务编排，只做三件事——拼路径、发请求、把响应解析成模型。

```python
from qqbotsdk.api.group.messages import send_group_messages, recall_group_messages
from qqbotsdk.model.group.messages import SendGroupMessagesRequest

resp = await send_group_messages(
    group_openid,
    SendGroupMessagesRequest(msg_type=0, content="hi", msg_id=msg_id, msg_seq=1),
)
print(resp.id, resp.timestamp)

await recall_group_messages(group_openid, resp.id)  # 无响应体, 返回 None
```

> 日常业务建议直接用 [app.md](app.md) 的 `ctx.reply()` / `ctx.send()`；API 层留给需要精细控制的场景。

## 约定

| 规则 | 说明 |
|---|---|
| 路径参数 | 一律作为**位置参数**（`group_openid`、`channel_id`、`message_id`…），不进请求模型 |
| 请求体 | `payload: XxxRequest`，内部 `model_dump(exclude_none=True)` |
| 查询参数 | GET/DELETE 也走 `payload=`，内部 `model_dump(exclude_none=True)` 放到 `params=` |
| 响应 | `XxxResponse.model_validate(result)` |
| 无响应体 | 返回 `None`（204 / 201 / 202），但仍会读取响应以释放连接 |
| 鉴权 | 由 `qqbotsdk.api.core.session` 自动注入，无需手写请求头 |
| 命名 | 函数名与模型一一对应：`get_panels` ↔ `GetPanelsRequest` / `GetPanelsResponse` |

## 请求要传齐，拼错会立刻报错

请求模型 `extra="forbid"`，禁止未知字段；响应模型则宽容未知字段，服务端加字段不会让解析失败：

```python
SendGroupMessagesRequest(contnet="hi")  # ValidationError: contnet
```

## 错误处理

所有错误统一走 `qqbotsdk.errors` 的三级异常（`QQBotAPIError` / `QQBotAuthError` / `QQBotGatewayError`），并透传 `trace_id`。**HTTP 429 自动退避重试**（最多 3 次，优先 `Retry-After`，总等待 ≤ 30 秒）。详见 [errors.md](errors.md)。

```python
from qqbotsdk.errors import QQBotAPIError

try:
    await send_group_messages(group_openid, request)
except QQBotAPIError as exc:
    print(exc.status, exc.err_code, exc.message, exc.trace_id)
```

## 分页

列表接口统一用 `cursor` + `limit`（部分用 `before`/`after` 或 `start_index`，见各接口说明），`limit` 有各自上限：

```python
from qqbotsdk.api.group.manage import get_group_members
from qqbotsdk.model.group.member import GetGroupMembersRequest

cursor = None
while True:
    page = await get_group_members(group_openid, GetGroupMembersRequest(cursor=cursor))
    for member in page.members or []:
        print(member.member_openid)
    cursor = page.next_cursor
    if not cursor:
        break
```

## 会话

`qqbotsdk.api.core.session` 是懒加载单例，签名与 `aiohttp.ClientSession` 一致；进程退出前建议 `await session.close()`：

```python
from qqbotsdk.api.core import session

# ... 业务调用 ...

await session.close()
```

## 接口索引

按域拆分。每个域一页，列出**全部接口**的签名、HTTP 路由、请求/响应模型与字段说明。

| 分组 | 详情页 | 覆盖内容 |
|---|---|---|
| 鉴权与会话 | [api/auth.md](api/auth.md) | `get_access_token` / `get_authorization` / `session` / 429 重试 / 错误检查 |
| 机器人基础 | [api/bot.md](api/bot.md) | `get_gateway` / `get_me` / `generate_url_link` / 网关地址获取 |
| 群聊与群管理 | [api/group.md](api/group.md) | 群消息、富媒体上传、成员、禁言、黑名单、入群审批、自动审批策略 |
| 单聊 | [api/user.md](api/user.md) | 单聊消息、流式消息、富媒体上传 |
| 素材管理 | [api/media.md](api/media.md) | 图片素材 prepare / 直传 / complete / 列表 / 删除 |
| 菜单与面板 | [api/menu-panel.md](api/menu-panel.md) | 全局自定义菜单、指令面板 |
| 互动 | [api/interaction.md](api/interaction.md) | 消息按钮 / 快捷菜单回包 |
| 频道域 | [api/guild.md](api/guild.md) | 频道、子频道、成员、身份组、消息、表情表态、公告、精华、日程、论坛、私信、音频 |

> 频道域接口在可选发行包 `qqbotsdk-guild-py` 里（`pip install "qqbotsdk-py[guild]"`），其余都在核心包。
