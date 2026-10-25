# 配置与订阅

`.env` 环境变量与 `intents.toml` 事件订阅。完整字段参考只在本文。

## .env 配置

SDK 启动时自动加载项目根目录的 `.env`，`APPID`/`APPSECRET` 缺失启动即报错：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret

BASE_URL=https://api.bot.qq.com   # 可选，官方 API 地址
TIMEOUT=5000                      # 可选，HTTP 请求超时（毫秒）
INTENTS_FILE=intents.toml         # 可选，事件订阅配置文件路径
INTENTS=                          # 可选，订阅掩码直传（十进制或 0x 十六进制），优先于 intents.toml
```

| 字段 | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `app_id` | `APPID` | 必填 | 缺失启动即 ValueError |
| `app_secret` | `APPSECRET` | 必填 | 同上 |
| `base_url` | `BASE_URL` | `https://api.bot.qq.com` | 官方 API 根地址 |
| `timeout` | `TIMEOUT` | `5000`（毫秒） | 转为 aiohttp `ClientTimeout(total=…)` |
| `intents_file` | `INTENTS_FILE` | `intents.toml` | 事件订阅配置路径 |
| `intents` | `INTENTS` | 空 | 订阅掩码直传，见[掩码直传](#掩码直传) |

`Config` 是 frozen dataclass，`Bot()` 构造时一次性读齐；handler 可标注 `config: Config` 注入。

## 事件订阅（intents.toml）

SDK 启动时读取 `intents.toml` 计算订阅掩码。订阅粒度就是下面表格里的大类（Intents 分组），把某组设为 `true` 即订阅该组下的全部事件：

```toml
GROUP_AND_C2C_EVENT = true   # 群/单聊消息与关注事件
INTERACTION = true           # 互动事件（卡片按钮回调）
GUILDS = false               # 频道/子频道增删改
```

QQ 网关只认分组位掩码，**组内单个事件无法单独开关**——能收到哪些事件由订阅了哪些分组决定（各组包含哪些事件见[事件 payload 对照](/docs/api/events.md)）。分组与特权要求：

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

## 掩码直传

不想用配置文件的，可以直接传订阅掩码，三种入口按优先级取先命中者：

1. **`Bot` 参数**（推荐写法，`Intent` 是 `IntFlag` 可直接 OR）：

   ```python
   from qqbotsdk import Bot, Intent

   bot = Bot(intents=Intent.GROUP_AND_C2C_EVENT | Intent.INTERACTION)
   ```

2. **`INTENTS` 环境变量**：十进制或 `0x` 十六进制字符串，如 `INTENTS=1073741824` 或 `INTENTS=0x40000000`；

3. 都没给才回落 `intents.toml`。

掩码原样下发给网关，含 `Intent` 枚举未收录的位时仅告警不拦截（平台可能新增 SDK 尚未收录的分组）。`Intent` 从包顶层导出（`from qqbotsdk import Intent`），各位值见上面的分组表。
