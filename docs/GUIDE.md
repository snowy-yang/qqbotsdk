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

SDK 启动时读取 `intents.toml` 计算订阅掩码，把想收的事件改成 `true` 即可。分组与特权要求：

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

事件名到 payload dataclass 的完整对照见 [API.md](API.md#事件-payload)。

## 接入方式选择

| | WebSocket | Webhook |
|---|---|---|
| 网络要求 | 能访问外网即可，本地开发友好 | 需公网可达 + HTTPS，仅支持 80/443/8080/8443 端口 |
| 配置 | 无额外配置 | 平台回调地址填 `https://<域名>:<端口><WEBHOOK_PATH>` |
| 连接维护 | SDK 自动心跳、断线指数退避重连并 RESUME 续传 | SDK 处理 Ed25519 验签、op=13 验证应答、60s TTL 事件去重 |
| 适用 | 长驻进程、需要会话与重连保障 | 无状态部署、回调型服务 |

两种方式下 handler 的写法完全一致，切换只需改 `CONNECTER`。

## 编写 handler

用装饰器把 handler 注册到 `EventEmitter`，事件名即线上 payload 的 `t` 名（如 `GROUP_AT_MESSAGE_CREATE`）。三种写法可混用：

```python
from qqbotsdk import EventEmitter, EventQueue, Inject

ee = EventEmitter(EventQueue())

# 方式一：裸参数，d 为原始事件 dict
@ee.on("GROUP_AT_MESSAGE_CREATE")
async def raw(d):
    print(d)

# 方式二：标注 payload dataclass，拿到解析后的对象
from qqbotsdk.payloads import GroupAtMessage

@ee.on("GROUP_AT_MESSAGE_CREATE")
async def typed(msg: GroupAtMessage):
    print(msg.group_openid, msg.user_openid, msg.content)

# 方式三：依赖注入
from qqbotsdk.api import BotApi
from qqbotsdk.events import Event

@ee.on("GROUP_AT_MESSAGE_CREATE")
async def di(event: Event, api: Inject[BotApi]):
    await api.post_group_message(event.group_id, content="收到", msg_id=event.message_id)
```

handler 参数按标注解析的完整规则：

| 参数标注 | 得到 |
|---|---|
| payload dataclass（如 `GroupAtMessage`） | 解析后的 dataclass 对象；未收录事件回退原始 dict |
| `Event` | 事件封装对象（`.raw`/`.data`/`.typed`/`.user_id`/`.group_id`/`.content`/`.message_id`） |
| `Inject[T]` | DI 容器解析的 `T`（如 `BotApi`）；解析失败回退传原始 dict |
| 无标注 | 原始事件 dict |

注意：

- 业务事件（op=0）处理器的**返回值不会回流**，回复消息请在 handler 里显式调 API。
- 单个 handler 抛异常只记录日志，不影响同事件其他 handler 和主循环。
- 未订阅（intents.toml 为 `false`）的事件不会到达 handler。

## 发消息

### 被动回复（最常用）

携带 `msg_id`（回复某条消息）或 `event_id`（响应某类事件，二选一）即为被动回复，**不需要任何消息频率白名单**：

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
- **handler 没被触发**：检查 intents.toml 对应事件是否为 `true`；群/单聊事件需开通对应能力；频道消息事件区分公私域。
- **想收原始数据**：handler 裸参数或标 `Event`，`event.raw` 是完整线上 payload（含 op/t/d）。
- **日志**：SDK 用 loguru 输出中文日志，连接、重连、API 失败、handler 异常均有记录，可直接用 loguru 配置格式与落盘。
