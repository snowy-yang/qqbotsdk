# 上层框架 `qqbotsdk.app`

业务方日常只碰这一层：监听 → 分发 → 注入 → 中间件 → 快捷调用。

```python
from qqbotsdk.app import Bot, Context

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    await ctx.reply("收到")


bot.run()
```

## Bot

```python
Bot(
    *,
    intents: Intents = DEFAULT_INTENTS,   # 订阅的事件位
    url: str | None = None,               # 省略则自动 GET /gateway 获取
    auto_reconnect: bool = True,
)
```

| 方法 | 说明 |
|---|---|
| `@bot.on("事件名")` | 精确注册；事件名见 [events.md](events.md)；`"*"` 表示全部 Dispatch |
| `@bot.on_message(group=True, c2c=True)` | 语法糖：群 @ 消息 / 群消息（`group`）与单聊消息（`c2c`） |
| `@bot.on_ready()` | READY 与 RESUMED 都触发 |
| `@bot.on_error()` | `async def h(ctx: Context | None, exc: BaseException)`，handler/中间件异常都进这里 |
| `@bot.middleware` | 洋葱中间件，`async def mw(ctx, call_next)` |
| `await bot.start()` / `await bot.stop()` | 异步生命周期（`stop()` 幂等） |
| `bot.run()` | 阻塞式，内部 `asyncio.run(bot.start())` |
| `bot.ws` | 当前 `QQBotWebSocket`，未启动时为 `None` |

## Context（注入到 handler）

| 成员 | 说明 |
|---|---|
| `ctx.event` | 已解析的 typed 事件模型；未建模事件为 `None` |
| `ctx.payload` | 原始 `GatewayPayload`，含 `event_id`（`payload.id`）、序号 `s`、事件名 `t` |
| `ctx.state` | `dict`，中间件与 handler 共享的请求级状态 |
| `ctx.bot` | 反向访问 `Bot` |
| `ctx.event_name` | `payload.t` |
| `ctx.group_openid` / `ctx.user_openid` | 从事件体里取场景 openid |
| `await ctx.reply(content, *, msg_seq=None, keyboard=None, seq_key=None)` | 被动回复，自动处理锚点与序号，可带内嵌键盘 |
| `await ctx.send(content)` | 主动消息（不带 `event_id`/`msg_id`） |

### reply 的锚点规则

1. 优先 `payload.id`（事件 ID）→ 填 `event_id`；
2. 否则回退 `d.id`（消息 ID）→ 填 `msg_id`；
3. 两者互斥，请求体里只会出现一个；
4. 都取不到 → 返回 `None`，**不会**退化成主动消息（不消耗主动推送配额）；
5. `msg_seq` 按锚点自增（1、2、3…，LRU 上限 512）；显式传入则覆盖并把计数推进到该值。平台上限是群聊 5 次、单聊 4 次，超出会被拒发。

`msg_seq` 计数**按锚点全局共享**，不随 `Bot` 实例隔离：同一进程里多个 `Bot` 命中同一锚点会继续往下排，而不是各自从 1 重来。自己拼请求直连 `send_group_messages` 时，先登记一次就不会让后面的 `ctx.reply` 撞上 40054005：

```python
# 手工直连发过一条之后登记, 避免后面的 ctx.reply 撞上同一个序号
seq = ctx.bot.next_msg_seq(anchor_id)

# 或者用显式 seq_key, 与 ctx.reply(..., seq_key="q1") 共用一份计数
seq = ctx.bot.next_msg_seq("shared", seq_key="q1")
```

只对这三个事件可回复：`GROUP_AT_MESSAGE_CREATE`、`GROUP_MESSAGE_CREATE`、`C2C_MESSAGE_CREATE`。

`keyboard` 用来在**被动回复**里带按钮，不必绕开框架直连 `send_group_messages`：

```python
from qqbotsdk.app import callback, keyboard, row

await ctx.reply("来答一道题", keyboard=keyboard(row(callback("选项 A", "a"))))
```

## ctx.api（场景门面）

`ctx.api` 绑定当前事件的场景（群 / 单聊），常见操作一行完成：

```python
@bot.on_message()
async def on_message(ctx: Context) -> None:
    msg_id = await ctx.api.send("主动消息")  # 返回消息 id
    await ctx.api.send_markdown("## 标题\n正文", keyboard=build_keyboard())
    await ctx.api.send_card(
        title="标题",
        description="描述",
        url="https://example.com",
        pic_url="https://example.com/a.png",
    )
    file_info = await ctx.api.upload_image("a.png")  # 上传图片拿 file_info
    await ctx.api.send_media(file_info, content="看图")
    await ctx.api.recall(msg_id)
```

| 方法 | 说明 | 返回 |
|---|---|---|
| `ctx.api.scene` | `"group"` / `"c2c"` / `"other"` | — |
| `send(content, *, keyboard=None)` | 主动文本（`msg_type=0`） | 消息 id |
| `send_markdown(content, *, keyboard=None)` | 主动 Markdown（`msg_type=2`） | 消息 id |
| `send_card(*, title, description, url, pic_url)` | 图文卡片（`msg_type=8`，`tuwen`） | 消息 id |
| `send_media(file_info, *, content="")` | 富媒体（`msg_type=7`） | 消息 id |
| `reply(content, *, msg_seq=None, keyboard=None, seq_key=None)` | 被动回复，等价 `ctx.reply()` | 消息 id 或 `None` |
| `recall(message_id)` | 撤回自己发的消息 | — |
| `upload_image(path)` | 分片上传图片，返回 `file_info` | `file_info` |
| `approve_join_request(member_openid=None, *, join_request_id=None)` | 通过入群申请（`member_openid` 默认取自事件） | — |
| `decline_join_request(member_openid=None, *, reject_reason=None, add_to_blacklist=False)` | 拒绝入群申请 | — |
| `ack_interaction(code=0)` | 回应消息按钮 / 快捷菜单互动 | — |

### 场景判定

| 事件体里有 | 场景 |
|---|---|
| `group_openid` | `group` |
| `author.user_openid`（单聊消息） | `c2c` |
| 顶层 `openid`（`FRIEND_ADD`、`C2C_MSG_RECEIVE` 等） | `c2c` |
| 都没有 | `other`（调用场景方法抛 `ValueError`） |

### 注意

- **`send*` 都是主动消息**（不带 `event_id`/`msg_id`），受频控约束；被动回复用 `reply()`。
- 按钮通过 `keyboard=` 传入，推荐用 [`qqbotsdk.app.keyboard`](#键盘构建) 的构建器拼装。
- `upload_image` 会算 `md5` / `sha1` / 前 10MB 的 `md5`，按 `parts` 逐片 PUT 后合并；目前只支持图片，分片串行上传。
- **QQ 没有「好友申请审核」接口**：加机器人即自动成为好友，`FRIEND_ADD` 只是通知，直接 `ctx.api.send()` 打招呼即可。
- `ack_interaction` 只有 `type=11`（消息按钮）与 `type=12`（快捷菜单）需要回应，否则客户端一直 loading；`code`：`0` 成功 / `1` 操作失败 / `2` 操作频繁 / `3` 重复操作 / `4` 没有权限 / `5` 仅管理员。

## 键盘构建

手拼键盘要套 `Keyboard → KeyboardContent → Row → Button → Action → RenderData` 六层，用 helper 一行搞定：

```python
from qqbotsdk.app import callback, command, confirm_modal, keyboard, link, row

KB = keyboard(
    row(
        callback("签到", "/signin", style="primary"),
        link("官网", "https://example.com"),
    ),
    row(
        command("帮助", "/help"),
        callback("清空", "/clear", style="danger", modal=confirm_modal("确定清空吗？")),
    ),
)

await ctx.api.send_markdown("## 今日签到", keyboard=KB)
```

| helper | 说明 |
|---|---|
| `callback(label, data, *, style, visited_label, permission, modal, group_id, ...)` | 回调按钮，点击后把 `data` 回传并触发 `INTERACTION_CREATE` |
| `link(label, url, ...)` | 跳转按钮，`url` 必须 `https://` |
| `command(label, data, *, enter=True, reply=True, anchor=None, ...)` | 指令按钮，点击后把 `data` 填进输入框（单聊可用） |
| `confirm_modal(content, *, confirm_text, cancel_text)` | 二次确认弹窗，传给 `callback(modal=...)` |
| `row(*buttons)` | 一行按钮 |
| `keyboard(*rows_or_buttons, max_per_row=5)` | 组装键盘；直接传按钮时按 `max_per_row` 自动切行 |
| `KeyboardBuilder()` | 链式构建：`.row(...)` / `.button(...)` / `.build()` |
| `everyone()` / `only_admin()` / `only_users(*ids)` / `only_roles(*ids)` | 按钮权限语法糖，返回 `Permission`（见下节） |

样式：`style="default"｜"primary"｜"danger"｜"positive"`，也接受常量 `STYLE_DEFAULT` / `STYLE_PRIMARY` / `STYLE_DANGER` / `STYLE_POSITIVE`。

约束（自动校验并抛 `ValueError`）：

- 最多 5 行、每行最多 5 个按钮；
- 不传 `button_id` 时，组装键盘时自动分配 `btn-1`、`btn-2`…（同一键盘内唯一）；
- 按钮文字最多 10 个字符（由模型校验）。

### 按钮权限语法糖

`permission=` 要记 `type` 的数字（`0` 指定用户 / `1` 管理员 / `2` 所有人 / `3` 指定身份组），容易记混。四个工厂函数把它变成可读的名字，**都返回 `Permission`**，可直接塞进 `permission=`：

```python
from qqbotsdk.app import callback, everyone, only_admin, only_roles, only_users

callback("签到", "/signin", permission=everyone())  # 所有人
callback("管理", "/admin", permission=only_admin())  # 仅管理员
callback("私聊", "/dm", permission=only_users("user_openid"))  # 指定用户
callback("内部", "/inner", permission=only_roles("role_id"))  # 指定身份组
```

| 糖 | 等价显式写法 |
|---|---|
| `everyone()` | `Permission(type=2)` |
| `only_admin()` | `Permission(type=1)` |
| `only_users(*user_ids)` | `Permission(type=0, specify_user_ids=[...])` |
| `only_roles(*role_ids)` | `Permission(type=3, specify_role_ids=[...])` |

要点：

- **只约束"可点击"，不约束"可见"**：`only_admin()` 是"仅管理员可点"。
- **不改默认行为**：不传 `permission=` 时仍是所有人。
- **参数为空抛 `ValueError`**（`only_users()` / `only_roles()` 不传 id 时谁都点不了，直接报错）。
- **跨场景**：`only_users` 参数在群里传群成员 `member_openid`、单聊传 `user_openid`、频道传 `user_id`；`only_roles` 是**频道域**概念，群聊/单聊用 `only_users`。
- **可退出**：糖只是便利入口，`permission=Permission(...)` 始终可用；返回的 `Permission` 也能继续 `model_copy(update=...)`。

## 中间件（洋葱模型）

```python
@bot.middleware
async def timing(ctx: Context, call_next) -> None:
    ctx.state["start"] = time.perf_counter()
    await call_next()  # 不调用即拦截
    print("耗时", time.perf_counter() - ctx.state["start"])
```

- 先注册的中间件在**外层**（先进后出）；
- 不调用 `call_next()` 即终止该事件的后续处理；
- 抛出异常 → 进 `on_error`。

## 阻断

handler 返回 `False` 时，同一事件的**后续 handler 不再执行**（中间件仍正常收尾）：

```python
@bot.on_message()
async def only_admin(ctx: Context) -> bool | None:
    if not ctx.state.get("is_admin"):
        return False  # 阻断后续 handler
    return None  # None/True 都表示继续
```

## 错误处理

```python
from qqbotsdk.errors import QQBotAPIError, QQBotError


@bot.on_error()
async def on_error(ctx: Context | None, exc: BaseException) -> None:
    if isinstance(exc, QQBotAPIError):
        logger.warning(
            f"{ctx.event_name} 失败: {exc.err_code} {exc.message} trace={exc.trace_id}"
        )
    elif isinstance(exc, QQBotError):
        logger.exception(exc)
    else:
        raise exc  # 未知异常可以继续抛，由默认 logger 兜底
```

未注册 `on_error` 时，异常由框架 `logger.exception` 记录，**不会**中断连接。

## 并发与生命周期

- 每个 Dispatch 在独立 `asyncio.Task` 里执行，不阻塞收包与心跳；
- handler 里禁止同步阻塞调用（`time.sleep`、同步 IO）；
- `stop()` 会关闭 ws、取消并回收未完成的 handler 任务；在 handler 里 `await bot.stop()` 是安全的。

## 订阅范围

默认 `DEFAULT_INTENTS` = 群与单聊消息 + 公域频道消息 + 频道成员 + 交互事件。

只要群聊/单聊时可以收窄，避免申请不需要的权限：

```python
from qqbotsdk.ws import Intents

bot = Bot(intents=Intents.GROUP_AND_C2C_EVENT | Intents.INTERACTION)
```

鉴权时传了无权限的 intents，网关会直接断开（关闭码 4013/4014），见 [ws.md](ws.md)。
