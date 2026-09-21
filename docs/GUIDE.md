# qqbotsdk 使用指南

面向使用者：从零开始接入 QQ 官方机器人，到收发消息、富媒体与常见问题。
API 细节见 [API.md](API.md)，内部架构见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 接入准备

1. 到 [QQ 开放平台](https://q.qq.com) 注册开发者账号并创建机器人，拿到 `AppID` 与 `AppSecret`（即 `.env` 里的 `APPID`/`APPSECRET`）。
2. 确认机器人的可用场景，这决定了你能收哪些事件、发哪些消息：
   - **群 / 单聊（v2 接口）**：需要在开放平台开通对应能力，事件与消息接口均用 openid（`group_openid` / `user_openid`），与用户的 QQ 号互不可见。
   - **频道公域机器人**：只能收 `AT_MESSAGE_CREATE`（@机器人才触发），发消息必须带 `msg_id` 被动回复。
   - **频道私域机器人**：可订阅 `GUILD_MESSAGES`（全量消息）与论坛事件，可主动发消息、撤回消息。

## 安装

项目未发布到 PyPI，从 Gitea 仓库安装（或克隆到本地后用路径安装）：

```bash
uv add git+https://gitea.4i.hk/hhhge/qqbotsdk          # 从仓库安装
uv add /path/to/qqbotsdk                               # 本地路径安装
```

要求 Python ≥ 3.13。

## 配置

在项目根目录放 `.env`（SDK 启动时自动加载，`APPID`/`APPSECRET` 缺失启动即报错）：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret
CONNECTER=websocket               # websocket 或 webhook，默认 websocket

BASE_URL=https://api.bot.qq.com   # 可选，官方 API 地址
TIMEOUT=5000                      # 可选，HTTP 请求超时（毫秒）
INTENTS_FILE=intents.toml         # 可选，事件订阅配置文件路径

WEBHOOK_HOST=0.0.0.0              # 以下仅 webhook 接入时生效
WEBHOOK_PORT=8080
WEBHOOK_PATH=/qqbot/webhook
```

## 事件订阅（intents.toml）

SDK 启动时读取 `intents.toml` 计算订阅掩码。订阅粒度就是下面表格里的大类（Intents 分组），把某组设为 `true` 即订阅该组下的全部事件：

```toml
GROUP_AND_C2C_EVENT = true   # 群/单聊消息与关注事件
INTERACTION = true           # 互动事件（卡片按钮回调）
GUILDS = false               # 频道/子频道增删改
```

QQ 网关只认分组位掩码，**组内单个事件无法单独开关**——能收到哪些事件由订阅了哪些分组决定（各组包含哪些事件见 [API.md](API.md#事件名--dataclass-对照)）。分组与特权要求：

| 分组 | 位掩码 | 说明 |
|---|---|---|
| `GUILDS` | 1 << 0 | 频道/子频道增删改 |
| `GUILD_MEMBERS` | 1 << 1 | 成员增删改 |
| `GUILD_MESSAGES` | 1 << 9 | 频道全量消息，**仅私域机器人** |
| `GUILD_MESSAGE_REACTIONS` | 1 << 10 | 频道表情表态 |
| `DIRECT_MESSAGE` | 1 << 12 | 频道私信 |
| `GROUP_AND_C2C_EVENT` | 1 << 25 | 群/单聊消息与关注事件（群机器人核心） |
| `INTERACTION` | 1 << 26 | 互动事件 |
| `MESSAGE_AUDIT` | 1 << 27 | 消息审核结果 |
| `FORUMS_EVENT` | 1 << 28 | 论坛事件，**仅私域机器人** |
| `AUDIO_ACTION` | 1 << 29 | 音频播放/上麦下麦 |
| `PUBLIC_GUILD_MESSAGES` | 1 << 30 | 频道公域消息（AT_MESSAGE_CREATE） |

分组名即 `Intent` 枚举成员名。配置只接受 `分组名 = true/false`；拼错的分组名、非布尔值，以及旧版"表内逐事件开关"的写法都会在启动时直接抛 `ValueError`（与其静默少订阅，不如启动即报错）。文件缺失则告警并按不订阅任何事件启动。

## 接入方式选择

| | WebSocket | Webhook |
|---|---|---|
| 网络要求 | 能访问外网即可，本地开发友好 | 需公网可达 + HTTPS，仅支持 80/443/8080/8443 端口 |
| 配置 | 无额外配置 | 平台回调地址填 `https://<域名>:<端口><WEBHOOK_PATH>` |
| 连接维护 | SDK 自动心跳、断线指数退避重连并 RESUME 续传；服务端约 1 小时会断开连接，SDK 会在临到期前（约 50 分钟）主动重连续传 | SDK 处理 Ed25519 验签、op=13 验证应答、60s TTL 事件去重 |
| 适用 | 长驻进程、需要会话与重连保障 | 无状态部署、回调型服务 |

两种方式下 handler 的写法完全一致，切换只需改 `CONNECTER`。

## 编写 handler

用装饰器把 handler 注册到 `EventEmitter`，事件名即线上 payload 的 `t` 名（如 `GROUP_AT_MESSAGE_CREATE`）。三种写法可混用：

```python
from qqbotsdk import EventEmitter

ee = EventEmitter()

# 方式一：裸参数，d 为原始事件 dict
@ee.on("GROUP_AT_MESSAGE_CREATE")
async def raw(d):
    print(d)

# 方式二：标注 payload dataclass，拿到解析后的对象
from qqbotsdk.payloads import GroupAtMessage

@ee.on("GROUP_AT_MESSAGE_CREATE")
async def typed(msg: GroupAtMessage):
    print(msg.group_openid, msg.user_openid, msg.content)

# 方式三：参数注入，标注组件类型即拿到实例
from qqbotsdk.api import BotApi
from qqbotsdk.events import Event

@ee.on("GROUP_AT_MESSAGE_CREATE")
async def di(event: Event, api: BotApi):
    await api.post_group_message(event.group_id, content="收到", msg_id=event.message_id)
```

handler 参数按标注解析的完整规则：

| 参数标注 | 得到 |
|---|---|
| payload dataclass（如 `GroupAtMessage`） | 解析后的 dataclass 对象；未收录事件回退原始 dict |
| `Event` | 事件封装对象（`.raw`/`.data`/`.typed`/`.user_id`/`.group_id`/`.content`/`.message_id`/`.event_id`） |
| 组件类型（`BotApi`/`Session`/`Config` 等） | `emitter.services` 中按类型登记的实例；未登记回退传原始 d |
| 无标注 | 原始 d（即事件 dict） |

注意：

- 只有**业务事件（op=0）**会分发给你的 handler；协议帧（HELLO/READY/INVALID_SESSION/op=13）由 SDK 的协议处理器就地处理，不触达 handler（`Ready` 是例外，它既是握手结果也是可监听的业务事件）。
- 业务事件处理器的**返回值不会回流**，回复消息请在 handler 里显式调 API。
- 单个 handler 抛异常只记录日志，不影响同事件其他 handler 和主循环。
- 所在分组未订阅（intents.toml 中为 `false`）的事件不会到达 handler。
- 自定义组件也能注入：`ee.services[MyService] = MyService(...)` 登记后，handler 形参标注 `MyService` 即可拿到实例。

### 后台并发 handler

默认同一事件的所有 handler 串行执行，某个慢 handler 会延迟后续事件。调用密集、不关心先后顺序的 handler 可加 `background=True` 丢进后台任务，事件流不再等它：

```python
@ee.on("GROUP_AT_MESSAGE_CREATE", background=True)
async def slow_work(msg: GroupAtMessage, api: BotApi):
    ...  # 耗时处理，不阻塞其他事件的分发
```

代价是同一事件内 handler 间失去先后保证，且返回值不回流（本就只对协议事件回流），因此仅用于业务 handler。进程退出时 `run_loop` 会统一取消在飞的后台任务。

## 发消息

### 被动回复（最常用）

携带 `msg_id`（回复某条消息）或 `event_id`（响应某类事件，二选一）即为被动回复，**不需要任何消息频率白名单**。两个 id 来源不同：`msg_id` 是消息事件体里的 `d.id`；`event_id` 是**网关推送最外层**的 id（`event.event_id`，形如 `INTERACTION_CREATE:uuid`），不是事件体里的裸 UUID：

- 群聊：收到消息后 **5 分钟**内可回复，同一 `msg_id` 最多 **5 次**；
- 单聊：**60 分钟**内可回复，同一 `msg_id` 最多 **4 次**；
- 同一条消息多次回复必须递增 `msg_seq`（相同 `msg_id`+`msg_seq` 会发送失败）；
- 被动回复同样受内容审核。

```python
await api.post_group_message(
    group_openid, content="你好", msg_id=msg.id, msg_seq=1,
)
```

### 主动消息

不带 `msg_id`/`event_id` 即主动消息，有额外频控（群/单聊每日每对象 1000 条），且默认关闭，需在开放平台申请。用户可在资料卡关闭主动推送（对应 `C2C_MSG_REJECT`/`GROUP_MSG_REJECT` 事件，关闭后发送会失败）。

### 富媒体（图片/视频/语音/文件）

先上传拿 `file_info`，再作为 `media` 发送（此时 SDK 自动把 `msg_type` 置为 7，`content` 作媒体下方的文字）：

```python
upload = await api.upload_group_file(
    group_openid, file_type=1, url="https://example.com/pic.png",
)
await api.post_group_message(
    group_openid, content="看图", msg_id=msg.id, media=upload,
)
```

`file_type`：1 图片、2 视频、3 语音、4 文件。也可在 `upload_*_file` 传 `srv_send_msg=True` 让上传即发送。

### Markdown 等其他类型

`post_group_message`/`post_c2c_message` 支持 `**extra` 透传官方 body 字段，例如 markdown（会覆盖默认的 `msg_type`）：

```python
await api.post_group_message(group_openid, content="# 标题\n正文",
                             msg_id=msg.id, msg_type=2)
```

### Markdown 与按钮（msg_type=2）

`button()`/`keyboard()`（`from qqbotsdk.api import button, keyboard`）构造内嵌按钮，配合 `markdown=` 一起发（msg_type 自动置 2）：

```python
await api.post_group_message(
    group_openid,
    markdown="## 标题\n**加粗**正文",        # 与 content 互斥
    keyboard=keyboard(
        button("点我", data="我的按钮数据"),                 # 单按钮独占一行
        [button("赞", data="like"), button("踩", data="dislike")],  # 列表同行并排
    ),
    msg_id=msg.id,
)
```

- `button(label, data, *, type=1, permission=2, style=1)`：`type` 1 回调（点击推 `INTERACTION_CREATE`）、0 跳转链接（data 为 url）、2 指令（往输入框插入 data）；`permission` 2 所有人 / 1 管理员 / 0 指定用户；`label` 官方限 10 字以内；要补嵌套字段（如 `visited_label`、`prompt`）直接修改返回的 dict。

**处理按钮点击**：点击回调推 `INTERACTION_CREATE` 事件，`inter.button_data` 即被点按钮的 `data`：

```python
@ee.on("INTERACTION_CREATE")
async def on_button(inter: Interaction, event: Event, api: BotApi):
    # 必须应答，否则用户端按钮一直 loading（inter.id 是事件体里的互动 id）
    await api.respond_interaction(inter.id)
    await api.post_group_message(
        inter.group_openid, content=f"你点了：{inter.button_data}",
        event_id=event.event_id,
    )
```

- **`event_id` 要取网关帧最外层的 id（`event.event_id`，形如 `INTERACTION_CREATE:uuid`），不能用事件体里的裸 UUID `inter.id`**——`inter.id` 只用于 `respond_interaction`，这是官方文档点名的常见坑；
- 需要在 intents.toml 开启 `INTERACTION` 分组；
- Markdown 有平台权限要求，无权限时发送会抛 `ApiError`（业务 code 304036/40034127），按需回退纯文本。

### 撤回

- 群/单聊（v2）：发出 **2 分钟**内可撤回（`withdraw_group_message`/`withdraw_c2c_message`）；
- 频道：仅私域机器人可撤回（`withdraw_channel_message`，`hide_tip=True` 隐藏撤回小灰条）。

## 运行与部署

```bash
uv run python main.py
```

- **WebSocket**：进程常驻即可；SDK 自动处理鉴权（IDENTIFY，断线自动 RESUME）、心跳与重连。
- **Webhook**：平台回调地址要求公网 HTTPS，本地调试建议用反向代理或内网穿透；开放平台会先发 op=13 验证请求，SDK 自动完成签名应答。

## 常见问题

- **启动后频繁重连 / READY 收不到**：QQ 网关接口有频率限制（code 100017），连续重启需间隔约 1 分钟；SDK 已内置退避，等即可。
- **`ApiError`**：HTTP ≥400 时抛出，`e.status`/`e.code`/`e.message` 可用于排查（如被动回复超时、msg_seq 重复、内容审核不通过）。
- **日志出现 `TokenError: 获取 access_token 失败`**：appid/secret 配置错误或被平台拒绝，`code`/`message` 就是 QQ 返回的真实原因，对照官方错误码排查即可。
- **handler 没被触发**：检查 intents.toml 中该事件所属分组是否为 `true`；群/单聊事件需开通对应能力；频道消息事件区分公私域。
- **想收原始数据**：handler 裸参数或标 `Event`，`event.raw` 是完整线上 payload（含 op/t/d）。
- **日志**：SDK 用 loguru 输出中文日志，连接、重连、API 失败、handler 异常均有记录，可直接用 loguru 配置格式与落盘。
