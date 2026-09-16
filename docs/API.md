# qqbotsdk API 参考

按公开使用面组织。上手流程见 [GUIDE.md](GUIDE.md)，分层与装配见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 顶层导出

```python
from qqbotsdk import (
    main, run_loop,          # 入口（组件在 run_loop 显式装配）
    EventEmitter, BaseProtocol, EventQueue,   # 分发层
    Config, Connecter,       # 配置与连接器接口
)
```

| 名称 | 说明 |
|---|---|
| `main(emitter=None)` | 同步入口：装配组件并阻塞运行，Ctrl+C 优雅退出 |
| `run_loop(emitter=None)` | 异步入口：`asyncio.run(run_loop(ee))` 的内部实现，可自行 await |
| `EventEmitter(queue)` | 分发主体，`@ee.on(...)` 注册 handler |
| `ee.services` | `dict[type, Any]`，按类型登记可注入组件；`run_loop` 装配 SDK 内置组件，也可登记自定义类型 |
| `EventQueue()` | 事件/应答队列；自建 emitter 时传入，`run_loop` 复用同一实例 |
| `Config` | frozen dataclass，环境变量一次性读齐（见下文） |
| `Connecter` | 连接适配器 Protocol（接口），按 `CONNECTER` 自动选择实现 |
| `BaseProtocol` | 协议层抽象基类，自定义协议处理器时继承并实现 `register(emitter)` |

子包按需导入：

```python
from qqbotsdk.api import BotApi, ApiError
from qqbotsdk.payloads import GroupAtMessage, EVENT_TYPES, parse_event
from qqbotsdk.events import Event
```

## EventEmitter

```python
ee = EventEmitter(EventQueue())

@ee.on("GROUP_AT_MESSAGE_CREATE")     # DISPATCH 事件用 t 名
@ee.on("INVALID_SESSION")             # 协议事件用 Opcode 名（IDENTIFY/RESUME/HEARTBEAT/...）
async def handler(...): ...
```

- **事件命名**：op=0（DISPATCH）按 payload 的 `t` 名路由；其余按 `Opcode` 名路由。协议事件（op≠0）已由内置协议层处理，一般只需监听业务事件；handler 返回 dict 时协议事件的返回值会回流给 ws 发送（业务事件不会）。
- **异常隔离**：handler 异常就地记录（loguru），不影响同事件其他 handler 与主循环。
- **`ee.handle(payload)`**：同步分发并返回首个 handler 的非空返回值，供协议层应答 op=13 等场景，业务代码不用。

### handler 参数注入约定

按参数类型标注解析，可任意混用：

| 标注 | 得到 | 未命中时 |
|---|---|---|
| payload dataclass（`payloads` 中的类型） | `Event.typed` 解析对象 | 回退传原始 dict |
| `Event` | 事件封装对象 | — |
| 组件类型（`BotApi`/`Session`/`Config` 等已登记进 `ee.services` 的类型） | 登记的实例 | 回退传原始 dict |
| 无标注 | 原始事件 dict | — |

## Event

`from qqbotsdk.events import Event`，一条 DISPATCH 事件的轻量封装，属性兼容群（openid）与频道两套字段名：

| 属性 | 说明 |
|---|---|
| `.raw` | 完整线上 payload（含 op/t/d） |
| `.data` | `d` 的 dict 拷贝 |
| `.typed` | `d` 的 dataclass 解析结果（未知事件类型为 dict） |
| `.type` | 事件 t 名 |
| `.user_id` | 用户标识（兼容 `user_id`/`from_user_id`） |
| `.group_id` | `group_openid` |
| `.content` | 消息文本 |
| `.message_id` | `d["id"]`，消息事件的被动回复凭据（msg_id） |
| `.event_id` | 推送信封顶层的事件 id（与 op/t/d 平级，形如 `INTERACTION_CREATE:uuid`）；非消息事件（`INTERACTION_CREATE`/`GROUP_ADD_ROBOT` 等）的被动回复凭据只有这里能拿到，事件体里的裸 UUID 不行（官方点名的常见坑） |

## Config

`Config.load()` 从环境变量一次性读齐（frozen，启动后不变）：

| 字段 | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `app_id` | `APPID` | 必填 | 缺失启动即 ValueError |
| `app_secret` | `APPSECRET` | 必填 | 同上 |
| `connecter` | `CONNECTER` | `websocket` | 仅允许 `websocket`/`webhook` |
| `base_url` | `BASE_URL` | `https://api.bot.qq.com` | 官方 API 根地址 |
| `timeout` | `TIMEOUT` | `5000`（毫秒） | 转为 aiohttp `ClientTimeout(total=…)` |
| `intents_file` | `INTENTS_FILE` | `intents.toml` | 事件订阅配置路径 |
| `webhook_host` | `WEBHOOK_HOST` | `0.0.0.0` | webhook 监听地址 |
| `webhook_port` | `WEBHOOK_PORT` | `8080` | webhook 监听端口 |
| `webhook_path` | `WEBHOOK_PATH` | `/qqbot/webhook` | webhook 回调路径 |

## BotApi

`from qqbotsdk.api import BotApi`。经参数注入（`api: BotApi`）。自动附带 `Authorization: QQBot <token>` 鉴权头并刷新 token；HTTP ≥400 抛 `ApiError`。

### 通用

| 方法 | 说明 |
|---|---|
| `request(method, path, **kwargs)` | 通用请求，kwargs 透传 aiohttp（`json=`/`params=` 等） |
| `get` / `post` / `delete` / `put` / `patch`(path, **kwargs) | `request` 快捷方式 |
| `me()` | 机器人自身信息（GET /users/@me） |
| `respond_interaction(interaction_id, code=0)` | 回应互动事件（PUT /interactions/{id}）；按钮点击（INTERACTION_CREATE type=11）收到后必须回应，否则客户端持续 loading，同一 id 仅可回应一次 |

常量：`MSG_TYPE_TEXT=0`、`MSG_TYPE_MARKDOWN=2`、`MSG_TYPE_MEDIA=7`；`FILE_TYPE_IMAGE=1`、`FILE_TYPE_VIDEO=2`、`FILE_TYPE_VOICE=3`、`FILE_TYPE_FILE=4`。

按钮构造：`button(label, data, *, type=1, permission=2, style=1)` 生成单个按钮 dict，`keyboard(*rows)` 组装为 `keyboard=` 参数（单按钮独占一行，按钮列表同行并排）。点击回调经 `INTERACTION_CREATE` 事件处理：`Interaction.button_data` 取被点按钮的 `data`，`Interaction.id` 用于 `respond_interaction`，**被动回复的 `event_id` 用 `Event.event_id`（网关帧最外层 id），不能用 `Interaction.id`**。

### v2 群聊（群 openid）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_group_message(group_openid, content="", msg_id=None, msg_seq=1, media=None, event_id=None, markdown=None, keyboard=None, **extra)` | POST /v2/groups/{group_openid}/messages | `msg_id`/`event_id` 二选一即被动回复（`event_id` 支持 GROUP_ADD_ROBOT / INTERACTION_CREATE 等事件）；`media` 传上传返回的 `{"file_info": …}`（自动 msg_type=7）；`markdown` 为字符串或完整 dict（自动 msg_type=2，与 content 互斥）；`keyboard` 为内嵌键盘 `{"content": {"rows": [...]}}` 或 `{"id": …}`；其余字段经 `extra` 透传 |
| `upload_group_file(group_openid, file_type, url, srv_send_msg=False)` | POST /v2/groups/{group_openid}/files | 富媒体上传，返回含 `file_info`；`srv_send_msg=True` 上传即发送 |
| `withdraw_group_message(group_openid, message_id)` | DELETE /v2/groups/{group_openid}/messages/{message_id} | 发出 2 分钟内可撤回 |
| `mute_group_member(group_openid, mute_expire_at)` | POST /v2/groups/{group_openid}/restrict_chat_setting | `mute_expire_at` 为 RFC3339 到期时间；传早于当前的时间即解禁 |

### v2 单聊（用户 openid）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_c2c_message(openid, content="", msg_id=None, msg_seq=1, media=None, event_id=None, markdown=None, keyboard=None, **extra)` | POST /v2/users/{openid}/messages | 同 `post_group_message` |
| `upload_c2c_file(openid, file_type, url, srv_send_msg=False)` | POST /v2/users/{openid}/files | 同 `upload_group_file` |
| `withdraw_c2c_message(openid, message_id)` | DELETE /v2/users/{openid}/messages/{message_id} | 2 分钟内可撤回 |

### 频道消息（channel_id / guild_id）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_channel_message(channel_id, content="", msg_id=None, msg_seq=1, image=None, **extra)` | POST /channels/{channel_id}/messages | `image` 为图片 URL；embed/ark/markdown 等经 `extra` 透传 |
| `withdraw_channel_message(channel_id, message_id, hide_tip=False)` | DELETE /channels/{channel_id}/messages/{message_id} | **仅私域机器人**；`hide_tip` 对应官方 `hidetip` |
| `put_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | PUT …/reactions/{type}/{emoji_id} | `emoji_type=1` 系统表情，`emoji_id` 为序号字符串 |
| `delete_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | DELETE …/reactions/{type}/{emoji_id} | 删除自己的表态 |

### 频道管理

| 方法 | 端点 | 说明 |
|---|---|---|
| `create_guild_announce(guild_id, channel_id, message_id, announces_type=0, **extra)` | POST /guilds/{guild_id}/announces | `announces_type`：0 成员公告 / 1 欢迎公告；推荐频道公告经 extra（与消息公告互斥） |
| `delete_guild_announce(guild_id, message_id)` | DELETE /guilds/{guild_id}/announces/{message_id} | 推荐频道公告传 `message_id="all"` |
| `pin_channel_message(channel_id, message_id)` | PUT /channels/{channel_id}/pins/{message_id} | 添加精华消息 |
| `unpin_channel_message(channel_id, message_id)` | DELETE /channels/{channel_id}/pins/{message_id} | 移出精华消息 |
| `get_channel_pins(channel_id)` | GET /channels/{channel_id}/pins | 精华消息列表 |
| `get_channel_schedules(channel_id, since=None)` | GET /channels/{channel_id}/schedules | 默认当天日程；`since` 毫秒时间戳 |
| `get_channel_schedule(channel_id, schedule_id)` | GET /channels/{channel_id}/schedules/{schedule_id} | 单个日程 |
| `create_channel_schedule(channel_id, name, start_timestamp, end_timestamp, jump_channel_id, remind_type="0", description="")` | POST /channels/{channel_id}/schedules | 时间为毫秒时间戳字符串；`remind_type` "0" 不提醒 / "1" 开始时；请求体自动包在 `schedule` 字段；单管理员每天限 10 次 |
| `update_channel_schedule(channel_id, schedule_id, **fields)` | PATCH /channels/{channel_id}/schedules/{schedule_id} | `fields` 为 schedule 内字段透传 |
| `delete_channel_schedule(channel_id, schedule_id)` | DELETE /channels/{channel_id}/schedules/{schedule_id} | 删除日程 |
| `mute_guild_member(guild_id, user_id, mute_seconds=0)` | PATCH /guilds/{guild_id}/members/{user_id}/mute | 禁言秒数（上限 28 天），0 解禁 |

### 频道查询

| 方法 | 端点 |
|---|---|
| `get_guild(guild_id)` | GET /guilds/{guild_id} |
| `get_guild_channels(guild_id)` | GET /channels/{guild_id}/channels |
| `get_channel(channel_id)` | GET /channels/{channel_id} |
| `get_guild_roles(guild_id)` | GET /guilds/{guild_id}/roles |
| `get_guild_member(guild_id, user_id)` | GET /guilds/{guild_id}/members/{user_id} |

### ApiError

`ApiError(RuntimeError)`，HTTP ≥400 时抛出：

| 属性 | 说明 |
|---|---|
| `.status` | HTTP 状态码 |
| `.code` | 官方业务 code（响应体中的 `code`） |
| `.message` | 官方错误描述 |

鉴权阶段（换取 access_token）的失败抛 `TokenError`（`from qqbotsdk.token import TokenError`），与 `ApiError` 同构（`RuntimeError` 子类，同样携带 `.status`/`.code`/`.message`）——appid/secret 配置错误在这里暴露 QQ 返回的真实原因。

## 事件 payload

`qqbotsdk.payloads` 定义事件 `d` 的 dataclass。handler 标注类型即得解析对象；未知事件类型回退原始 dict。所有字段均可为 None（线上缺省即 None），嵌套 `author` 自动解析为 `Author`。

### 事件名 → dataclass 对照

| intents 分组 | 事件 t 名 | dataclass |
|---|---|---|
| GROUP_AND_C2C_EVENT | `C2C_MESSAGE_CREATE` | `C2CMessage` |
| | `GROUP_AT_MESSAGE_CREATE` | `GroupAtMessage` |
| | `FRIEND_ADD` / `FRIEND_DEL` | `FriendAdd` / `FriendDel` |
| | `GROUP_ADD_ROBOT` / `GROUP_DEL_ROBOT` | `GroupAddRobot` / `GroupDelRobot` |
| | `C2C_MSG_REJECT` / `C2C_MSG_RECEIVE` | `C2CMsgReject` / `C2CMsgReceive` |
| | `GROUP_MSG_REJECT` / `GROUP_MSG_RECEIVE` | `GroupMsgReject` / `GroupMsgReceive` |
| PUBLIC_GUILD_MESSAGES | `AT_MESSAGE_CREATE` | `AtMessage` |
| | `PUBLIC_MESSAGE_DELETE` | `MessageDelete` |
| GUILD_MESSAGES（私域） | `MESSAGE_DELETE` | `MessageDelete` |
| DIRECT_MESSAGE | `DIRECT_MESSAGE_CREATE` | `DirectMessage` |
| GUILDS | `GUILD_CREATE` / `GUILD_UPDATE` / `GUILD_DELETE` | `Guild` |
| | `CHANNEL_CREATE` / `CHANNEL_UPDATE` / `CHANNEL_DELETE` | `Channel` |
| GUILD_MESSAGE_REACTIONS | `MESSAGE_REACTION_ADD` / `…_REMOVE` | `MessageReaction` |
| MESSAGE_AUDIT | `MESSAGE_AUDIT_PASS` / `…_REJECT` | `MessageAudit` |
| INTERACTION | `INTERACTION_CREATE` | `Interaction` |
| FORUMS_EVENT（私域） | `FORUM_THREAD_CREATE` / `…_UPDATE` / `…_DELETE` | `ForumThread` |
| | `FORUM_POST_CREATE` / `…_DELETE` | `ForumPost` |
| | `FORUM_REPLY_CREATE` / `…_DELETE` | `ForumReply` |
| AUDIO_ACTION | `AUDIO_START` / `AUDIO_FINISH` / `AUDIO_ON_MIC` / `AUDIO_OFF_MIC` | `AudioAction` |
| —（DISPATCH 协议事件） | `READY` | `Ready` |

未收录的事件（如私域 `MESSAGE_CREATE`、`DIRECT_MESSAGE_DELETE`、`GUILD_MEMBER_*`）handler 收到原始 dict；新增事件在 `payloads.py` 加 dataclass 并登记 `EVENT_TYPES` 即可。

### 常用 dataclass 字段

```python
Author            # id, user_openid, member_openid, username, bot
GroupAtMessage    # id, content, group_openid, author, timestamp
C2CMessage        # id, content, author, attachments, timestamp
AtMessage         # id, content, channel_id, guild_id, author, member, timestamp
DirectMessage     # 同 AtMessage
```

- `GroupAtMessage.user_openid` / `C2CMessage.user_openid`：便利属性，从 `author.member_openid`/`author.user_openid` 取发言人标识。
- 群/单聊场景拿不到用户真实 QQ 号，只有 openid；频道场景 `Author.id`/`username` 有效。
- 其余事件 dataclass 为 2~5 个平铺字段的同构结构（openid/时间戳/信息 dict），字段名即官方文档字段。

`parse_event(t, d)`：把事件 `d` 解析为对应 dataclass（`Event.typed` 的内部实现），`EVENT_TYPES` 为事件名 → 类的完整登记表。

## 内部模块索引

维护者视角的分层与装配见 [ARCHITECTURE.md](ARCHITECTURE.md)：

| 模块 | 职责 |
|---|---|
| `connecter.py` | `WebsocketConnecter` / `WebhookConnecter`：接入归一为事件流入、reply 流出 |
| `ws_protocol.py` | IDENTIFY/RESUME 鉴权、apscheduler 心跳、会话序列号 |
| `webhook_protocol.py` | op=13 验证应答 |
| `queue.py` / `session.py` / `token.py` / `crypto.py` | 队列、ws 会话状态、token 缓存、Ed25519 签名 |
| `model.py` | Opcode、payload 类型、Intent 位掩码 |
| `__init__.py` | `main`/`run_loop` 入口与组件显式装配 |
