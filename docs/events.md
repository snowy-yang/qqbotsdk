# 事件与 Intents

## 事件从哪来

网关下发的每一帧结构一致：

```json
{ "id": "event_id", "op": 0, "s": 42, "t": "GROUP_AT_MESSAGE_CREATE", "d": { } }
```

| 字段 | 含义 |
|---|---|
| `op` | 操作码，`0` = Dispatch（业务事件） |
| `s` | 序号，心跳与 Resume 需要 |
| `t` | 事件名 |
| `id` | 事件 ID（被动回复时作为 `event_id`） |
| `d` | 事件体，**事件模型只描述这一部分** |

信封模型：`qqbotsdk.ws.payload.GatewayPayload`；`READY` 的事件体是 `ReadyContent`。

## Intents（订阅位）

```python
from qqbotsdk.ws import DEFAULT_INTENTS, Intents

intents = Intents.GROUP_AND_C2C_EVENT | Intents.PUBLIC_GUILD_MESSAGES
```

| 成员 | 位 | 覆盖事件 |
|---|---|---|
| `GUILDS` | 1<<0 | GUILD_CREATE/UPDATE/DELETE、CHANNEL_CREATE/UPDATE/DELETE |
| `GUILD_MEMBERS` | 1<<1 | GUILD_MEMBER_ADD/UPDATE/REMOVE |
| `GUILD_MESSAGES` | 1<<9 | MESSAGE_CREATE、MESSAGE_DELETE（仅私域） |
| `GUILD_MESSAGE_REACTIONS` | 1<<10 | MESSAGE_REACTION_ADD/REMOVE |
| `DIRECT_MESSAGE` | 1<<12 | DIRECT_MESSAGE_CREATE/DELETE |
| `GROUP_MEMBER_EVENT` | 1<<24 | GROUP_MEMBER_ADD、GROUP_MEMBER_REMOVE、GROUP_JOIN_REQUEST |
| `GROUP_AND_C2C_EVENT` | 1<<25 | GROUP_AT_MESSAGE_CREATE、GROUP_MESSAGE_CREATE、GROUP_ADD_ROBOT、GROUP_DEL_ROBOT、GROUP_MSG_RECEIVE/REJECT、C2C_MESSAGE_CREATE、C2C_MSG_RECEIVE/REJECT、FRIEND_ADD/DEL、SUBSCRIBE_MESSAGE_STATUS |
| `INTERACTION` | 1<<26 | INTERACTION_CREATE |
| `MESSAGE_AUDIT` | 1<<27 | MESSAGE_AUDIT_PASS/REJECT |
| `FORUMS_EVENT` | 1<<28 | FORUM_*（仅私域） |
| `AUDIO_ACTION` | 1<<29 | AUDIO_START/FINISH/ON_MIC/OFF_MIC |
| `PUBLIC_GUILD_MESSAGES` | 1<<30 | AT_MESSAGE_CREATE、PUBLIC_MESSAGE_DELETE |

`DEFAULT_INTENTS` = `GROUP_AND_C2C_EVENT | PUBLIC_GUILD_MESSAGES | GUILD_MEMBERS | INTERACTION`。

只做群聊 / 单聊时用 `GROUP_BOT_INTENTS` = `GROUP_AND_C2C_EVENT | INTERACTION`，不含
任何频道位。`GUILD_MEMBERS` / `PUBLIC_GUILD_MESSAGES` 按官方说明是「基础事件、默认有
权限」，所以 `DEFAULT_INTENTS` 本身不会导致连接被拒；真正需要申请的是 `INTERACTION`
（消息按钮 / 快捷菜单）。

订阅了无权限的 intents，网关会断开（关闭码 4013/4014）；现在的异常文案会指明是
intents 权限问题，并提示去开放平台开通。

### 用 `INTENTS` 环境变量收窄订阅

不重新发版也能调整订阅范围，优先级 `Bot(intents=...)` > `INTENTS` > `DEFAULT_INTENTS`：

```ini
INTENTS=0x2000000          # 10 进制或 0x 十六进制掩码
```

```python
from qqbotsdk.app import Bot
from qqbotsdk.app.bot import resolve_intents

bot = Bot()  # 读 INTENTS
print(resolve_intents())  # 看看最终生效的掩码
```

> **注意 `GROUP_MEMBER_EVENT` (1<<24)**：官方「事件订阅与通知」总表没有收录这一位，
> 但 [群成员加入](https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/group_member_add.html)
> 与 [用户申请加群](https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/group_join_request.html)
> 的文档标注的 Intent 都是它。需要这两类事件时必须显式订阅，它不在默认值里：
>
> ```python
> bot = Bot(intents=DEFAULT_INTENTS | Intents.GROUP_MEMBER_EVENT)
> ```

## 事件模型与解析

两个注册表，按装了什么包决定用哪个：

| 注册表 | 事件数 | 适用包 |
|---|---|---|
| `qqbotsdk.model.event` | 16 | `qqbotsdk-py`：群聊 / 单聊 / 好友 / 订阅消息 / 互动 |
| `qqbotsdk.model.guild.event` | 40 | `qqbotsdk-guild-py`：频道 / 子频道 / 消息 / 成员 / 表情表态 / 审核 / 论坛 / 音频 |

## 常用便捷属性

几个「每个 bot 都要踩一次」的字段差异，SDK 已经归一：

| 属性 | 所在模型 | 作用 |
|---|---|---|
| `sender_openid` | `GroupMessageEventBase` / `C2CMessageCreateEvent` | 群聊取 `author.member_openid`，单聊取 `author.user_openid`，自动回退 |
| `button_data` | `InteractionCreateEvent` | 免去逐层钻 `data.resolved.button_data` |
| `button_id` | `InteractionCreateEvent` | 被点击按钮的 `id` |
| `clicker_openid` | `InteractionCreateEvent` | 群聊取 `group_member_openid`，单聊取 `user_openid` |

```python
@bot.on("INTERACTION_CREATE")
async def on_click(ctx: Context) -> None:
    print(ctx.event.button_data, ctx.event.clicker_openid)
    await ctx.api.ack_interaction(0)
```

```python
from qqbotsdk.model.event import EVENT_MODELS, parse_event

print(sorted(EVENT_MODELS))  # 16 个事件名
event = parse_event(payload)  # 未建模事件返回 None
```

频道域：

```python
from qqbotsdk.model.guild.event import EVENT_MODELS, parse_event
```

上层 `Bot` 已经替你做过解析：`ctx.event` 就是对应模型（频道事件在装了 guild 包时同样可用）。

## 在 handler 里按类型分支

```python
from qqbotsdk.app import Bot, Context
from qqbotsdk.model.event import GroupAtMessageCreateEvent

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    if isinstance(ctx.event, GroupAtMessageCreateEvent):
        print(ctx.event.group_openid, ctx.event.author.member_openid, ctx.event.content)
    await ctx.reply("ok")
```

## 直接解析未建模的事件

未建模的事件 `ctx.event` 为 `None`，但 `ctx.payload.d` 仍是原始字典：

```python
@bot.on("*")
async def on_any(ctx: Context) -> None:
    if ctx.event is None:
        print("未建模事件:", ctx.event_name, ctx.payload.d)
```

## 不连网关做测试

`Bot.dispatch()` 是公开方法，可以把一帧直接喂给 bot，无需假网关服务端；
`qqbotsdk.testing` 提供了更顺手的包装：

```python
from qqbotsdk.testing import dispatch, dispatch_frame, make_payload

await dispatch(bot, "GROUP_AT_MESSAGE_CREATE", {"id": "m1", "content": "hi"})
await dispatch_frame(bot, '{"op": 0, "t": "READY", "d": {}}')  # 直接贴网关日志
payload = make_payload("GROUP_AT_MESSAGE_CREATE", {...}, event_id=None)  # 验证回退分支
```
