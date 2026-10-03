# 事件处理

handler 的注册、参数注入约定与后台并发。注入约定表只在本文。

## 注册

用装饰器把 handler 注册到 `Bot`，事件名即线上 payload 的 `t` 名（如 `GROUP_AT_MESSAGE_CREATE`）。参数按类型标注注入，可任意混用：

```python
from qqbotsdk import Bot
from qqbotsdk.api import BotApi
from qqbotsdk.events import Event
from qqbotsdk.payloads import GroupAtMessage, Interaction

bot = Bot()


# 标注 payload dataclass，拿到解析后的对象
@bot.on("GROUP_AT_MESSAGE_CREATE")
async def typed(msg: GroupAtMessage):
    print(msg.group_openid, msg.user_openid, msg.content)


# payload 与组件任意组合；Event 拿完整信封（如按钮回调要 event_id）
@bot.on("INTERACTION_CREATE")
async def full(inter: Interaction, event: Event, api: BotApi):
    ...
```

handler 参数按标注解析的完整规则：

| 参数标注 | 得到 |
|---|---|
| payload dataclass（如 `GroupAtMessage`，全部类型见[事件 payload](/docs/api/events.md)） | 解析后的 dataclass 对象 |
| `Event` | 事件封装对象，只含信封语义（`.raw`/`.data`/`.typed`/`.type`/`.event_id`）；事件体字段请标注 payload dataclass 获取 |
| 组件类型（`BotApi`/`Bot`/`Session`/`Config` 等已登记进 `bot.services` 的类型） | 按类型登记的实例 |

无标注或标注以上三者皆非的形参会在分发时抛 `ValueError`（记日志、按 handler 隔离）——SDK 不注入原始数据：要事件体字段就标注 payload dataclass，要完整信封就标注 `Event`。

## 注册与分发语义

- 只有**业务事件（op=0）**会分发给你的 handler；协议帧（HELLO/READY/INVALID_SESSION/op=13）由 SDK 的协议处理器就地处理，不触达 handler（`Ready` 是例外，它既是握手结果也是可监听的业务事件）。
- 同一函数对同一事件重复注册只生效一次；handler 按注册顺序串行执行（`background=True` 的除外）。
- 业务事件处理器的**返回值不会回流**，回复消息请在 handler 里显式调 API。
- 单个 handler 抛异常只记录日志，不影响同事件其他 handler 和主循环。
- 所在分组未订阅（intents.toml 中为 `false`）的事件不会到达 handler（见[配置与订阅](/docs/guide/config.md)）。

## 后台并发 handler

默认同一事件的所有 handler 串行执行，某个慢 handler 会延迟后续事件。调用密集、不关心先后顺序的 handler 可加 `background=True` 丢进后台任务，事件流不再等它：

```python
@bot.on("GROUP_AT_MESSAGE_CREATE", background=True)
async def slow_work(msg: GroupAtMessage, api: BotApi):
    ...  # 耗时处理，不阻塞其他事件的分发
```

代价是同一事件内 handler 间失去先后保证，因此仅用于业务 handler。`bot.run()` 退出时统一取消在飞的后台任务。

## 自定义组件注入

`bot.services` 是 `dict[type, Any]` 组件登记表：SDK 启动时登记内置组件（`Bot`/`EventEmitter`/`EventQueue`/`Config`/`Session`/`ClientSession`/`AccessToken`/`BotApi`），你也可以登记自定义类型：

```python
bot = Bot()
bot.services[MyService] = MyService(...)   # 任意时机登记（启动前后皆可）


@bot.on("GROUP_AT_MESSAGE_CREATE")
async def with_service(msg: GroupAtMessage, svc: MyService):
    ...  # 形参标注 MyService 即拿到实例
```

services 命中在每条事件分发时实时判定，"先注册 handler、后登记组件"的顺序可用。
