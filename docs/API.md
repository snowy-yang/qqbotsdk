# qqbotsdk API 参考

按公开使用面组织。上手流程见 [GUIDE.md](GUIDE.md)，分层与装配见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 顶层导出

```python
from qqbotsdk import (
    main, run_loop,          # 入口（组件在 run_loop 显式装配）
    EventEmitter, EventQueue,   # 分发层
    BaseProtocol,            # 协议处理器接口（自定义接入方式时继承）
    Config, Connecter,       # 配置与连接器接口
)
```

| 名称 | 说明 |
|---|---|
| `main(emitter=None)` | 同步入口：装配组件并阻塞运行，Ctrl+C 优雅退出 |
| `run_loop(emitter=None)` | 异步入口：`asyncio.run(run_loop(ee))` 的内部实现，可自行 await |
| `EventEmitter(queue=None)` | 分发主体，`@ee.on(..., background=True)` 注册 handler（可选后台并发）；`queue` 不传自动创建 |
| `ee.services` | `dict[type, Any]`，按类型登记可注入组件；`run_loop` 装配 SDK 内置组件，也可登记自定义类型 |
| `EventQueue()` | 业务事件通道（连接层 → 分发层，单向）；`EventEmitter` 默认自建，需多处共享时手动传入（`ee.queue` 取实例） |
| `Config` | frozen dataclass，环境变量一次性读齐（见下文） |
| `Connecter` | 连接适配器抽象基类（ABC），按 `CONNECTER` 自动选择实现 |
| `BaseProtocol` | 协议处理器抽象基类（`protocol.py`），自定义接入方式时继承并实现 `on_frame(payload)` |

子包按需导入：

```python
from qqbotsdk.api import BotApi, ApiError
from qqbotsdk.payloads import GroupAtMessage, EVENT_TYPES, parse_event
from qqbotsdk.events import Event
```

## EventEmitter

```python
ee = EventEmitter()

@ee.on("GROUP_AT_MESSAGE_CREATE")     # 业务事件用 t 名（仅 op=0 会分发到这里）
async def handler(...): ...

@ee.on("GROUP_AT_MESSAGE_CREATE", background=True)   # 后台并发执行，不阻塞事件流
async def slow(...): ...
```

- **只分发业务事件**：`EventEmitter` 只处理 op=0（DISPATCH）事件，按 payload 的 `t` 名路由。协议帧（HELLO/READY/INVALID_SESSION/op=13 等）由各接入方式的协议处理器（`WebsocketProtocol`/`WebhookProtocol`）在连接器内就地处理，不进事件队列、也不会触达你的 handler。
- **注册与顺序**：同一函数对同一事件重复注册只生效一次；handler 按注册顺序串行执行（`background=True` 的除外）。
- **异常隔离**：handler 异常就地记录（loguru），不影响同事件其他 handler 与主循环。
- **后台并发**：`background=True` 的 handler 进后台任务，emit 不等它；同一事件内失去先后保证，仅用于业务 handler。`run_loop` 退出时统一取消在飞后台任务（`ee.close()`）。
- 业务 handler 的返回值不回流；回复消息请在 handler 里显式调 `BotApi`。

### handler 参数注入约定

按参数类型标注解析，可任意混用：

| 标注 | 得到 |
|---|---|
| payload dataclass（`payloads` 中的类型） | `Event.typed` 解析对象 |
| `Event` | 事件封装对象 |
| 组件类型（`BotApi`/`Session`/`Config` 等已登记进 `ee.services` 的类型） | 登记的实例 |

无标注或标注以上三者皆非的形参在分发时抛 `ValueError`（记日志、按 handler 隔离）——SDK 不注入原始 d，要事件体字段就标注 payload dataclass，要完整信封就标注 `Event`。

## Event

`from qqbotsdk.events import Event`，业务事件推送信封（op/t/d/id）的轻量封装，只封装信封语义、不做字段名映射；事件体字段请标注对应 payload dataclass（见下文）获取解析结果：

| 属性 | 说明 |
|---|---|
| `.raw` | 完整线上 payload（含 op/t/d） |
| `.data` | `d` 的 dict 拷贝 |
| `.typed` | `d` 的 dataclass 解析结果（未知事件类型为 dict） |
| `.type` | 事件 t 名 |
| `.event_id` | 推送信封顶层的事件 id（与 op/t/d 平级，形如 `INTERACTION_CREATE:uuid`）；非消息事件（`INTERACTION_CREATE`/`GROUP_ADD_ROBOT` 等）的被动回复凭据只有这里能拿到，事件体里的裸 UUID 不行（官方点名的常见坑）；消息事件的被动回复凭据是事件体的 `d.id`（payload 的 `.id` 字段，即 msg_id），不用这里 |

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

实现按域拆在 `qqbotsdk/api/` 包内（`core` 请求内核 + `v2`/`channel`/`guild`/`panel`/`group`/`audio`/`forum` 方法集组合成 `BotApi`），方法名与下表一致；429 限流自动重试（最多 3 次，优先 `Retry-After`，退避封顶 30s），401 强制刷新 token 后重试一次。

### 通用

| 方法 | 说明 |
|---|---|
| `request(method, path, **kwargs)` | 通用请求，kwargs 透传 aiohttp（`json=`/`params=` 等） |
| `get` / `post` / `delete` / `put` / `patch`(path, **kwargs) | `request` 快捷方式 |
| `me()` | 机器人自身信息（GET /users/@me） |
| `generate_url_link(callback_data=None)` | 生成机器人分享链接（POST /v2/generate_url_link），返回 `{"data": {"url": …}}`；用户经链接添加时 `callback_data`（≤32 字符）透传给开发者 |
| `respond_interaction(interaction_id, code=0)` | 回应互动事件（PUT /interactions/{id}）；按钮点击（INTERACTION_CREATE type=11）收到后必须回应，否则客户端持续 loading，同一 id 仅可回应一次 |

常量：`MSG_TYPE_TEXT=0`、`MSG_TYPE_MARKDOWN=2`、`MSG_TYPE_MEDIA=7`；`FILE_TYPE_IMAGE=1`、`FILE_TYPE_VIDEO=2`、`FILE_TYPE_VOICE=3`、`FILE_TYPE_FILE=4`；流式消息 `STREAM_INPUT_APPEND`/`STREAM_INPUT_REPLACE`、`STREAM_GENERATING=1`/`STREAM_FINISHED=10`、`STREAM_CONTENT_TEXT`/`STREAM_CONTENT_MARKDOWN`；音频 `AUDIO_STATUS_START=0`/`PAUSE=1`/`RESUME=2`/`STOP=3`；论坛 `FORUM_FORMAT_TEXT=1`/`HTML=2`/`MARKDOWN=3`/`JSON=4`。

按钮构造：`button(label, data, *, type=1, permission=2, style=1)` 生成单个按钮 dict，`keyboard(*rows)` 组装为 `keyboard=` 参数（单按钮独占一行，按钮列表同行并排）。点击回调经 `INTERACTION_CREATE` 事件处理：`Interaction.button_data` 取被点按钮的 `data`，`Interaction.id` 用于 `respond_interaction`，**被动回复的 `event_id` 用 `Event.event_id`（网关帧最外层 id），不能用 `Interaction.id`**。

### v2 群聊（群 openid）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_group_message(group_openid, content="", msg_id=None, msg_seq=1, media=None, event_id=None, markdown=None, keyboard=None, **extra)` | POST /v2/groups/{group_openid}/messages | `msg_id`/`event_id` 二选一即被动回复（`event_id` 支持 GROUP_ADD_ROBOT / INTERACTION_CREATE 等事件）；`media` 传上传返回的 `{"file_info": …}`（自动 msg_type=7）；`markdown` 为字符串或完整 dict（自动 msg_type=2，与 content 互斥）；`keyboard` 为内嵌键盘 `{"content": {"rows": [...]}}` 或 `{"id": …}`；其余字段经 `extra` 透传 |
| `upload_group_file(group_openid, file_type, url, srv_send_msg=False)` | POST /v2/groups/{group_openid}/files | 富媒体上传，返回含 `file_info`；`srv_send_msg=True` 上传即发送 |
| `withdraw_group_message(group_openid, message_id)` | DELETE /v2/groups/{group_openid}/messages/{message_id} | 发出 2 分钟内可撤回 |
| `mute_group_member(group_openid, mute_expire_at)` | POST /v2/groups/{group_openid}/restrict_chat_setting | `mute_expire_at` 为 RFC3339 到期时间；传早于当前的时间即解禁 |
| `prepare_group_upload(group_openid, file_type, file_size, file_name, md5, sha1, md5_10m)` | POST /v2/groups/{group_openid}/upload_prepare | 大文件分片预上传，返回 `upload_id`/`block_size`/各分片预签名 `parts`；逐片 PUT 后调 `finish_group_upload_part`，全部完成后携 `upload_id` 调 `upload_group_file` 合并；`md5_10m` 为文件前约 10MB 的 MD5 |
| `finish_group_upload_part(group_openid, upload_id, part_index, block_size=None, md5=None)` | POST …/upload_part_finish | 每个分片 PUT 成功后调用确认 |

### v2 单聊（用户 openid）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_c2c_message(openid, content="", msg_id=None, msg_seq=1, media=None, event_id=None, markdown=None, keyboard=None, **extra)` | POST /v2/users/{openid}/messages | 同 `post_group_message` |
| `upload_c2c_file(openid, file_type, url, srv_send_msg=False)` | POST /v2/users/{openid}/files | 同 `upload_group_file` |
| `withdraw_c2c_message(openid, message_id)` | DELETE /v2/users/{openid}/messages/{message_id} | 2 分钟内可撤回 |
| `post_c2c_stream_message(openid, content_raw="", *, stream_msg_id=None, index=0, input_state=STREAM_GENERATING, input_mode=None, content_type=STREAM_CONTENT_MARKDOWN, msg_id=None, event_id=None, msg_seq=None, is_wakeup=None)` | POST /v2/users/{openid}/stream_messages | 流式分批发送（AI 回复逐段下发）：首片不传 `stream_msg_id`，响应 `id` 即后续分片要携带的值，`index` 从 0 递增，以 `input_state=STREAM_FINISHED` 收尾；`input_mode="replace"` 时 `content_raw` 须以上游已下发前缀开头；`is_wakeup=True` 为召回消息，不校验被动回复有效期 |
| `prepare_c2c_upload(openid, …)` / `finish_c2c_upload_part(openid, …)` | POST /v2/users/{openid}/upload_prepare · upload_part_finish | 单聊分片上传，用法同群聊 `prepare_group_upload`/`finish_group_upload_part` |

### 群管理（群 openid）

多数接口要求机器人拥有群管理员身份；成员/黑名单/批量移除等能力官方标注"内邀接入中"，未开通时服务端返回业务码 11253。常量：`APPROVE`/`DECLINE`（审批动作）、`OP_ADD`/`OP_DEL`（黑名单/白名单操作）。

| 方法 | 端点 | 说明 |
|---|---|---|
| `get_group_info(group_openid)` | GET /v2/groups/{group_openid}/info | 群名称/简介/分类/标签/成员数 |
| `get_group_members(group_openid, cursor=None)` | GET …/members | 成员列表，每页最多 30 条，`next_cursor` 翻页（空串=末页） |
| `get_group_member(group_openid, member_openid)` | GET …/members/{member_openid} | 成员昵称/角色（member/owner/admin）/入群时间 |
| `get_group_bot_state(group_openid)` | GET …/bot_state | 机器人自身状态：入群时间、是否允许主动推送、群内消息接收设置、角色 |
| `remove_group_members(group_openid, member_openids, add_to_member_blacklist=False)` | POST …/batch_remove_members | 批量移除，单次最多 20 个，可选拉黑 |
| `get_group_join_requests(group_openid, cursor=None, limit=None)` | GET …/join_request_list | 入群申请列表（含验证问答），需群管理员；limit 默认 20 最大 50 |
| `review_group_join_request(group_openid, member_openid, op, join_request_id=None, reject_reason=None, add_to_member_blacklist=None)` | POST …/approval_join_request/{member_openid} | `op`：`APPROVE`/`DECLINE`；拒绝时可附理由并拉黑 |
| `get_group_mute_state(group_openid)` | GET …/restrict_chat_setting | 禁言状态：全员禁言规则（定时/周期）与被禁言成员列表 |
| `get_group_blacklist(group_openid, cursor=None, limit=None)` | GET …/member_blacklist | 黑名单列表，limit 默认 20 最大 100 |
| `update_group_blacklist(group_openid, op, member_openids)` | POST …/member_blacklist | `op`：`OP_ADD`/`OP_DEL`，单次最多 20 个；成员在群中时无法拉黑 |
| `get_join_approval_strategies(cursor=None, limit=None)` | GET /v2/groups/join_approval_strategy | 自动审批策略列表（机器人维度全局配置），按创建时间倒序 |
| `create_join_approval_strategy(*, group_openids=None, group_ids=None, is_enable=None, expire_at=None, remark=None)` | POST /v2/groups/join_approval_strategy | 关联群两种标识二选一（互斥，最多 100 个）；`is_enable` "on"/"off"；默认一年过期；仅机器人有群管理员身份时生效；返回 `strategy_id` |
| `update_join_approval_strategy(strategy_id, *, is_enable=None, expire_at=None, group_action=None, remark=None)` | PATCH …/{strategy_id} | 只传变更项；`group_action` 为 `{"op": "add"/"del", "group_openids": […]}`，群标识形式须与创建时一致 |
| `delete_join_approval_strategy(strategy_id)` | DELETE …/{strategy_id} | 删除策略 |
| `execute_join_approval_strategy(strategy_id)` | POST …/{strategy_id}/execute | 全量扫描关联群并自动通过白名单申请；异步约 10 分钟 |
| `update_join_approval_strategy_whitelist(strategy_id, op, whitelist_users)` | POST …/{strategy_id}/whitelist_users | QQ 号码字符串列表，单次最多 10000、上限 10 万 |

### 频道消息（channel_id / guild_id）

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_channel_message(channel_id, content="", msg_id=None, msg_seq=1, image=None, **extra)` | POST /channels/{channel_id}/messages | `image` 为图片 URL；embed/ark/markdown 等经 `extra` 透传 |
| `withdraw_channel_message(channel_id, message_id, hide_tip=False)` | DELETE /channels/{channel_id}/messages/{message_id} | **仅私域机器人**；`hide_tip` 对应官方 `hidetip` |
| `put_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | PUT …/reactions/{type}/{emoji_id} | `emoji_type=1` 系统表情，`emoji_id` 为序号字符串 |
| `delete_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | DELETE …/reactions/{type}/{emoji_id} | 删除自己的表态 |
| `create_dms(recipient_id, source_guild_id)` | POST /users/@me/dms | 创建私信会话（需与用户同频道），返回私信的 `guild_id`/`channel_id` |
| `post_dms_message(guild_id, content="", msg_id=None, msg_seq=1, image=None, **extra)` | POST /dms/{guild_id}/messages | 发私信，参数同 `post_channel_message`；主动消息每天单用户 2 条、累计 200 条，被动不限 |
| `withdraw_dms_message(guild_id, message_id, hide_tip=False)` | DELETE /dms/{guild_id}/messages/{message_id} | 撤回自己发的私信，**仅私域** |
| `get_channel_permissions(channel_id, user_id)` / `get_channel_role_permissions(channel_id, role_id)` | GET …/members/{user_id}/permissions · …/roles/{role_id}/permissions | 子频道权限位图（字符串） |
| `update_channel_permissions(channel_id, user_id, *, add=None, remove=None)` / `update_channel_role_permissions(channel_id, role_id, …)` | PUT 同路径 | `add`/`remove` 为字符串权限位图，至少传一个，需管理员权限 |

### 频道管理

| 方法 | 端点 | 说明 |
|---|---|---|
| `create_guild_announce(guild_id, channel_id, message_id, announces_type=0, **extra)` | POST /guilds/{guild_id}/announces | `announces_type`：0 成员公告 / 1 欢迎公告；推荐频道公告经 extra（与消息公告互斥） |
| `create_channel(guild_id, name, **fields)` | POST /guilds/{guild_id}/channels | 创建子频道，**私域**需管理员权限；`fields` 透传 type/sub_type/position/parent_id/private_type/speak_permission 等；触发 CHANNEL_CREATE |
| `update_channel(channel_id, **fields)` | PATCH /channels/{channel_id} | 修改子频道，**私域**；只传变更项；触发 CHANNEL_UPDATE |
| `delete_channel(channel_id)` | DELETE /channels/{channel_id} | 删除子频道，**私域**；不可恢复；触发 CHANNEL_DELETE |
| `delete_guild_announce(guild_id, message_id)` | DELETE /guilds/{guild_id}/announces/{message_id} | 推荐频道公告传 `message_id="all"` |
| `pin_channel_message(channel_id, message_id)` | PUT /channels/{channel_id}/pins/{message_id} | 添加精华消息 |
| `unpin_channel_message(channel_id, message_id)` | DELETE /channels/{channel_id}/pins/{message_id} | 移出精华消息 |
| `get_channel_pins(channel_id)` | GET /channels/{channel_id}/pins | 精华消息列表 |
| `get_channel_schedules(channel_id, since=None)` | GET /channels/{channel_id}/schedules | 默认当天日程；`since` 毫秒时间戳 |
| `get_channel_schedule(channel_id, schedule_id)` | GET /channels/{channel_id}/schedules/{schedule_id} | 单个日程 |
| `create_channel_schedule(channel_id, name, start_timestamp, end_timestamp, jump_channel_id, remind_type="0", description="")` | POST /channels/{channel_id}/schedules | 时间为毫秒时间戳字符串；`remind_type` "0" 不提醒 / "1" 开始时；请求体自动包在 `schedule` 字段；单管理员每天限 10 次 |
| `update_channel_schedule(channel_id, schedule_id, **fields)` | PATCH /channels/{channel_id}/schedules/{schedule_id} | `fields` 为 schedule 内字段透传 |
| `delete_channel_schedule(channel_id, schedule_id)` | DELETE /channels/{channel_id}/schedules/{schedule_id} | 删除日程 |
| `create_guild_role(guild_id, name="", color=None, hoist=None)` | POST /guilds/{guild_id}/roles | 创建身份组，返回 `{"role_id", "role"}`；`color` 为 ARGB 十进制 |
| `update_guild_role(guild_id, role_id, name=None, color=None, hoist=None)` | PATCH /guilds/{guild_id}/roles/{role_id} | 只传变更项；系统默认身份组不可改 |
| `delete_guild_role(guild_id, role_id)` | DELETE /guilds/{guild_id}/roles/{role_id} | 只能删除自建身份组 |
| `add_guild_member_role(guild_id, user_id, role_id)` / `remove_guild_member_role(…)` | PUT / DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id} | 授予/收回成员身份组 |
| `remove_guild_member(guild_id, user_id, add_blacklist=False, delete_history_msg_days=0)` | DELETE /guilds/{guild_id}/members/{user_id} | 踢人，**私域**需踢人权限；撤回消息仅支持 3/7/15/30 或 -1 全部 |
| `mute_guild(guild_id, mute_end_timestamp=None, mute_seconds=None)` | PATCH /guilds/{guild_id}/mute | 全员禁言，两个时间字段二选一；解除都传 "0" |
| `mute_guild_members(guild_id, user_ids, …)` | PATCH /guilds/{guild_id}/mute | 批量禁言（带 `user_ids`），单次最多 20 人 |
| `create_api_permission_demand(guild_id, channel_id, path, method, desc)` | POST /guilds/{guild_id}/api_permission/demand | 生成接口权限授权链接发到子频道，由频道管理员授权 |
| `mute_guild_member(guild_id, user_id, mute_seconds=0)` | PATCH /guilds/{guild_id}/members/{user_id}/mute | 禁言秒数（上限 28 天），0 解禁 |

### 频道查询

| 方法 | 端点 |
|---|---|
| `get_guild(guild_id)` | GET /guilds/{guild_id} |
| `get_me_guilds(before=None, after=None, limit=None)` | GET /users/@me/guilds |
| `get_guild_channels(guild_id)` | GET /channels/{guild_id}/channels |
| `get_guild_members(guild_id)` | GET /guilds/{guild_id}/members |
| `get_role_members(guild_id, role_id)` | GET /guilds/{guild_id}/roles/{role_id}/members |
| `get_channel_online_nums(channel_id)` | GET /channels/{channel_id}/online_nums |
| `get_guild_message_setting(guild_id)` | GET /guilds/{guild_id}/message/setting |
| `get_guild_api_permissions(guild_id)` | GET /guilds/{guild_id}/api_permission |
| `get_channel(channel_id)` | GET /channels/{channel_id} |
| `get_guild_roles(guild_id)` | GET /guilds/{guild_id}/roles |
| `get_guild_member(guild_id, user_id)` | GET /guilds/{guild_id}/members/{user_id} |

### 指令面板（斜线指令）与全局菜单

斜线指令面板即用户在聊天输入框输入 `/` 唤起的指令列表，支持 c2c（单聊）、group（群聊）、channel（文字子频道）、dm（频道私信）四种场景；c2c/group 支持 `target_type="specific"` 按指定对象生效（关联对象每次最多 20 个，详情最多查 1000 个），channel/dm 仅全局生效。一个机器人最多 20 个面板，每面板最多 20 个元素（`name` ≤14 字符、`desc` ≤30 字符）。常量：`SCOPE_C2C`/`SCOPE_GROUP`/`SCOPE_CHANNEL`/`SCOPE_DM`、`TARGET_ALL`/`TARGET_SPECIFIC`、`ITEM_COMMAND`/`ITEM_LINK`、`TARGET_OP_ADD`/`TARGET_OP_DEL`。

| 方法 | 端点 | 说明 |
|---|---|---|
| `create_panel(scope, panel, *, target_type=None, user_openids=None, group_openids=None, **extra)` | POST /v2/panels | 返回 `{"panel_id": …}`；`panel` 为 `{"items": [{"type": "command"/"link", "name", "desc", "only_admin", "link"}], "remark"}`，command 类型点击后 `name` 填入输入框，link 类型点击跳转 |
| `get_panels(scope, cursor=None, limit=None)` | GET /v2/panels | 分页列表（按设置时间倒序），返回 `records`/`next_cursor`（空串=末页）/`is_end`；`limit` 默认 20、最大 50 |
| `get_panel(panel_id)` | GET /v2/panels/{panel_id} | 面板详情，specific 面板另带关联的 `user_openids`/`group_openids` |
| `update_panel(panel_id, panel)` | PUT /v2/panels/{panel_id} | 整体覆盖元素与备注，不影响已关联对象；返回 `{"version": …}` |
| `delete_panel(panel_id)` | DELETE /v2/panels/{panel_id} | 删除面板，删除后对所有对象失效 |
| `update_panel_targets(panel_id, op, user_openids=None, group_openids=None)` | PUT /v2/panels/{panel_id}/target | `op`：`"add"`/`"del"`；`user_openids` 仅 c2c、`group_openids` 仅 group；channel/dm 与全局面板不支持 |
| `get_menu()` | GET /v2/menu | 查询全局自定义菜单（仅 C2C、对所有用户生效），返回 `{"version", "menu"}`；未设置过时 `menu` 为空 |
| `update_menu(menu=None)` | PUT /v2/menu | 整体覆盖菜单（≤10 项，子菜单 ≤5 且不可再嵌套）；`send_message` 类型点击后把文本（如 `/help`）填入输入框，常与斜线指令配合 |

### 音频与论坛（私域）

音频接口仅音频类机器人可用（需联系平台开通）；论坛仅论坛子频道，发帖/删帖为异步任务（返回 `task_id`，结果经 FORUM_* 事件推送）。

| 方法 | 端点 | 说明 |
|---|---|---|
| `control_channel_audio(channel_id, audio_url=None, text=None, status=AUDIO_STATUS_START)` | POST /channels/{channel_id}/audio | 播放控制（START/PAUSE/RESUME/STOP）；`audio_url`/`text` 仅 START 时传 |
| `put_channel_mic(channel_id)` / `delete_channel_mic(channel_id)` | PUT / DELETE /channels/{channel_id}/mic | 机器人上麦 / 下麦 |
| `get_channel_threads(channel_id)` | GET /channels/{channel_id}/threads | 帖子列表 `{"threads", "is_finish"}` |
| `get_channel_thread(channel_id, thread_id)` | GET …/threads/{thread_id} | 帖子详情 |
| `put_channel_thread(channel_id, title, content, format=FORUM_FORMAT_TEXT)` | PUT /channels/{channel_id}/threads | 发帖，`format` 为 FORUM_FORMAT_* 常量；返回 `task_id` |
| `delete_channel_thread(channel_id, thread_id)` | DELETE …/threads/{thread_id} | 删帖，返回 `task_id` |

### ApiError

`ApiError(RuntimeError)`，重试后仍失败（HTTP ≥400）时抛出：

| 属性 | 说明 |
|---|---|
| `.status` | HTTP 状态码 |
| `.code` | 官方业务 code（响应体中的 `code`） |
| `.message` | 官方错误描述 |

鉴权阶段（换取 access_token）的失败抛 `TokenError`（`from qqbotsdk.token import TokenError`），与 `ApiError` 同构（`RuntimeError` 子类，同样携带 `.status`/`.code`/`.message`）——appid/secret 配置错误在这里暴露 QQ 返回的真实原因。

## 事件 payload

`qqbotsdk.payloads` 定义事件 `d` 的 dataclass。handler 标注类型即得解析对象；未知事件类型回退原始 dict。所有字段均可为 None（线上缺省即 None），嵌套 `author` 自动解析为 `Author`。

### 事件名 → dataclass 对照

下表左列是 intents.toml 的订阅分组（订阅粒度即分组，组内事件无法单独开关），中列是同时属于该分组、会被一起推送的事件 `t` 名：

| intents 分组 | 事件 t 名 | dataclass |
|---|---|---|
| GROUP_AND_C2C_EVENT | `C2C_MESSAGE_CREATE` | `C2CMessage` |
| | `GROUP_AT_MESSAGE_CREATE` / `GROUP_MESSAGE_CREATE` | `GroupAtMessage` |
| | `FRIEND_ADD` / `FRIEND_DEL` | `FriendAdd` / `FriendDel` |
| | `GROUP_ADD_ROBOT` / `GROUP_DEL_ROBOT` | `GroupAddRobot` / `GroupDelRobot` |
| | `C2C_MSG_REJECT` / `C2C_MSG_RECEIVE` | `C2CMsgReject` / `C2CMsgReceive` |
| | `GROUP_MSG_REJECT` / `GROUP_MSG_RECEIVE` | `GroupMsgReject` / `GroupMsgReceive` |
| | `SUBSCRIBE_MESSAGE_STATUS` | `SubscribeMessageStatus` |
| GROUP_MEMBER_EVENT | `GROUP_MEMBER_ADD` / `GROUP_MEMBER_REMOVE` | `GroupMemberChange` |
| | `GROUP_JOIN_REQUEST`（仅机器人是群管理员时推送） | `GroupJoinRequest` |
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

未收录的事件（如私域 `MESSAGE_CREATE`、`DIRECT_MESSAGE_DELETE`、`GUILD_MEMBER_*`）没有对应 dataclass 可标注，请标注 `Event` 经 `.typed`（未知事件类型为 dict）或 `.raw` 访问；新增事件在 `payloads.py` 加 dataclass 并登记 `EVENT_TYPES` 即可。

`GROUP_MESSAGE_CREATE` 是群消息**全量模式**：需在开放平台开通"接收所有消息"权限，群里每条消息（不限 @机器人）都推送此事件，与 `GROUP_AT_MESSAGE_CREATE` 共用 `GroupAtMessage`。官方提示同一 msg_id 可能重复推送，业务侧需按 `id` 去重。

### 常用 dataclass 字段

```python
Author            # id, user_openid, member_openid, username, bot
GroupAtMessage    # id, content, group_openid, author, timestamp,
                  # message_type, message_scene, attachments, mentions, ark_data, msg_elements
C2CMessage        # id, content, author, attachments, timestamp
AtMessage         # id, content, channel_id, guild_id, author, member, timestamp
DirectMessage     # 同 AtMessage
GroupJoinRequest  # group_openid, join_request_id, member_openid, username, risk_tips,
                  # apply_at, apply_source, invited_by, verify_info, auto_approved, …
GroupMemberChange # timestamp, group_openid, member_openid, user_openid
```

- `GroupAtMessage.user_openid` / `C2CMessage.user_openid`：便利属性，从 `author.member_openid`/`author.user_openid` 取发言人标识。
- 群/单聊场景拿不到用户真实 QQ 号，只有 openid；频道场景 `Author.id`/`username` 有效。
- 其余事件 dataclass 为 2~5 个平铺字段的同构结构（openid/时间戳/信息 dict），字段名即官方文档字段。

`parse_event(t, d)`：把事件 `d` 解析为对应 dataclass（`Event.typed` 的内部实现），`EVENT_TYPES` 为事件名 → 类的完整登记表。

## 内部模块索引

维护者视角的分层与装配见 [ARCHITECTURE.md](ARCHITECTURE.md)：

| 模块 | 职责 |
|---|---|
| `connecter.py` | `WebsocketConnecter` / `WebhookConnecter`：接入归一为业务事件流入、出站帧流出 |
| `protocol.py` | `BaseProtocol` 协议处理器接口（`on_frame`，由连接适配器逐帧调用） |
| `ws_protocol.py` | IDENTIFY/RESUME 鉴权、会话语义与 `s` 序列号（心跳在 connecter 内） |
| `webhook_protocol.py` | op=13 验证应答 |
| `queue.py` / `session.py` / `token.py` / `crypto.py` | 业务事件通道、ws 会话状态、token 缓存、Ed25519 签名 |
| `model.py` | Opcode、payload 类型、Intent 位掩码 |
| `__init__.py` | `main`/`run_loop` 入口与组件显式装配 |
