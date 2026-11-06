# 0.x / 1.x → 2.x 迁移指南

2.0 是一次**破坏性重构**：单一发行包拆成三个、事件分发从「依赖注入的形参」改成
「一个 `Context` 入参」、API 层从「类方法」改成「模块级函数」。

这份文档按「你原来怎么写 → 现在怎么写」逐条对照。完整破坏性清单见
[CHANGELOG](../CHANGELOG.md)。

## 1. 安装与包名

| 1.x | 2.x |
|---|---|
| `pip install qqbotsdk-py`（单包全量） | `pip install qqbotsdk-py`（核心）+ 需要频道时 `pip install "qqbotsdk-py[guild]"` |

三个发行包共享 `qqbotsdk` 命名空间（PEP 420），可任意组合安装。频道域拆到了
`qqbotsdk-guild-py`，只装核心包时导入 `qqbotsdk.model.guild.*` 会失败。

包里没有 `__init__.py`：`import qqbotsdk` 能成功，但**装不全时报的错会很有误导性**
（表现为 `No module named 'qqbotsdk.api.core'`）。排障见
[README「安装不完整怎么办」](../README.md)。

## 2. 导入路径

| 1.x | 2.x |
|---|---|
| `from qqbotsdk import Bot` | `from qqbotsdk.app import Bot, Context` |
| `from qqbotsdk.api import BotApi` | 删除；用 `qqbotsdk.api.*` 的模块级函数，或上层 `ctx.api` |
| `from qqbotsdk.payloads import GroupAtMessage` | `from qqbotsdk.model.event import GroupAtMessageCreateEvent` |
| `from qqbotsdk.errors import ApiError` | `from qqbotsdk.errors import QQBotAPIError` |
| `from qqbotsdk.events import Event` | 删除；网关帧是 `qqbotsdk.ws.payload.GatewayPayload` |

## 3. handler 写法（改动最大的一处）

**1.x：靠形参标注做依赖注入**——`EventEmitter` 按类型把 payload、`BotApi`、自定义
组件塞进 handler 的参数里，还支持 dishka 的 `Inject[T]`。

**2.x：只有一个入参 `ctx: Context`**——事件、原始帧、API 门面都挂在它上面。

```python
# 1.x
from qqbotsdk import Bot
from qqbotsdk.api import BotApi
from qqbotsdk.payloads import GroupAtMessage

bot = Bot()


@bot.on("GROUP_AT_MESSAGE_CREATE")
async def on_group_message(msg: GroupAtMessage, api: BotApi) -> None:
    await api.post_group_message(
        msg.group_openid,
        content=f"你说：{msg.content}",
        msg_id=msg.id,
    )
```

```python
# 2.x
from qqbotsdk.app import Bot, Context
from qqbotsdk.model.event import GroupAtMessageCreateEvent

bot = Bot()


@bot.on_message()  # 等价于同时注册群聊 + 单聊消息事件
async def on_message(ctx: Context) -> None:
    event = ctx.event
    if isinstance(event, GroupAtMessageCreateEvent):
        await ctx.reply(f"你说：{event.content}")
```

要点：

- `@bot.on("GROUP_AT_MESSAGE_CREATE")` **仍然可用**，只是 handler 签名变了；`on_message()` 只是糖。
- `ctx.event` 是解析好的事件模型，未建模的事件是 `None`，原始字典在 `ctx.payload.d`。
- `ctx.api` 是按场景绑好的门面（群聊 / 单聊），不用再自己判断该调哪个接口。
- dishka 的 `Inject[T]` 注入已移除，需要依赖就自己拿 `ctx.bot` 或闭包捕获。

## 4. 发消息

### 被动回复（就是原来的 `msg_id` 参数）

```python
# 1.x
await api.post_group_message(group_openid, content="收到", msg_id=msg.id)

# 2.x：锚点、msg_seq 自动处理
await ctx.reply("收到")
```

`msg_seq` 不再需要自己维护——SDK 按锚点全局自增，命中 40054005 的概率降到 0。
需要跨进程/多实例共享计数或手工直连时，见 [app.md](app.md) 的 `seq_key`。

### Markdown / 富媒体 / 卡片

```python
# 1.x
await api.post_group_message(group, markdown="## 标题", msg_id=msg.id, keyboard=kb)
await api.post_group_message(group, media={"file_info": fi}, msg_id=msg.id)

# 2.x
await ctx.reply_markdown("## 标题", keyboard=kb)
await ctx.reply_media(file_info, content="看图")
```

要点：2.x 里 `msg_type` 会按填入的内容字段自动推导，不用再手写。

### 主动消息

```python
# 1.x
await api.post_group_message(group, content="主动推送")

# 2.x
await ctx.api.send("主动推送")  # 或 ctx.send("主动推送")
```

### 需要完全自定义请求体时

```python
from qqbotsdk.api.group import messages as group_messages

prepared = ctx.build_reply(markdown="**hi**", keyboard=kb)  # 只算不发
if prepared is not None:
    scene, openid, request = prepared
    await group_messages.send_group_messages(openid, request)
```

## 5. 回应按钮 / 快捷菜单

```python
# 1.x
await api.respond_interaction(inter.id, code=0)

# 2.x
await ctx.api.ack_interaction(0)  # interaction_id 自动从事件里取
```

按钮回调的数据：

```python
# 1.x
act.data.resolved["button_data"]

# 2.x
ctx.event.button_data  # 便捷属性，免去逐层钻
ctx.event.clicker_openid  # 群聊/单聊的 openid 归一
```

## 6. 事件订阅（intents）

| 1.x | 2.x |
|---|---|
| 项目根目录 `intents.toml` 按大类开关 | `Bot(intents=Intents.GROUP_AND_C2C_EVENT \| ...)` |
| `INTENTS` 环境变量（十进制 / `0x`） | **已恢复**：未显式传 `intents` 时读 `INTENTS` |
| — | 新增 `GROUP_BOT_INTENTS`（只做群聊 / 单聊时的推荐预设） |

```python
from qqbotsdk.ws import GROUP_BOT_INTENTS, Intents

bot = Bot(intents=GROUP_BOT_INTENTS)  # 群聊 + 互动
bot = Bot(intents=Intents.GROUP_AND_C2C_EVENT)  # 连按钮都不用
```

`INTENTS` 环境变量的优先级：`Bot(intents=...)` > `INTENTS` > `DEFAULT_INTENTS`。
运维可以不重新发版就收窄订阅。

订阅了没开通的 intent，网关会用关闭码 **4013 / 4014** 直接断开——现在异常文案会
说明是 intents 权限问题，并提示去开放平台开通。

## 7. 错误处理

```python
# 1.x
from qqbotsdk.errors import ApiError

try:
    ...
except ApiError as exc:
    if exc.code == 40034005:
        ...
```

```python
# 2.x
from qqbotsdk.errors import QQBotAPIError, codes

try:
    ...
except QQBotAPIError as exc:
    if exc.err_code == codes.MSG_ID_EXPIRED:
        ...
```

改动点：

- 异常名 `ApiError` → `QQBotAPIError`；
- 业务码属性 `.code` → **`.err_code`**（`.code` 在 2.x 里不再是业务码）；
- 新增 `qqbotsdk.errors.codes` 常量模块，不用再写魔法数字。

## 8. 通用 REST 调用

```python
# 1.x
await bot.call_api("GET", "/users/@me")

# 2.x
from qqbotsdk.api.core import session

async with session.request("GET", "/users/@me") as resp:
    data = await resp.json()
```

`session.request()` 与 `session.get()` / `post()` 等完全同构，同样走 429 重试。

## 9. 测试

| 1.x | 2.x |
|---|---|
| `EventEmitter` 可以手工喂事件 | `await bot.dispatch(payload)` 或 `qqbotsdk.testing.dispatch(bot, 事件名, 事件体)` |
| 自行构造假 registrar | `qqbotsdk.testing.make_payload` / `dispatch_frame` |
| 共享 HTTP 连接池难以替换 | `qqbotsdk.api.core.use_session(fake)` 整体替换 |

```python
from qqbotsdk.testing import dispatch


async def test_echo() -> None:
    bot = Bot()
    seen: list[str | None] = []

    @bot.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(ctx: Context) -> None:
        seen.append(ctx.payload.id)

    await dispatch(bot, "GROUP_AT_MESSAGE_CREATE", {"id": "m1", "content": "hi"})
    assert seen == ["evt-1"]
```

## 10. 迁移自查清单

- [ ] 所有 `from qqbotsdk import Bot` 改成 `from qqbotsdk.app import Bot, Context`
- [ ] 所有 handler 签名改成 `async def h(ctx: Context)`
- [ ] 形参注入的 payload 改成 `ctx.event`，`BotApi` 改成 `ctx.api`
- [ ] `msg_id=` 的被动回复改成 `ctx.reply()` / `ctx.reply_markdown()` / `ctx.reply_media()`
- [ ] `respond_interaction(id)` 改成 `ctx.api.ack_interaction(code)`
- [ ] `ApiError` → `QQBotAPIError`，`.code` → `.err_code`
- [ ] `intents.toml` 删除，改成 `Bot(intents=...)` 或 `INTENTS` 环境变量
- [ ] 只做群聊的 bot 改用 `GROUP_BOT_INTENTS`
- [ ] 频道相关导入确认已安装 `qqbotsdk-guild-py`
