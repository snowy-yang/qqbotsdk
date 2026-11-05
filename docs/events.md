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

订阅了无权限的 intents，网关会断开（关闭码 4013/4014）。

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
