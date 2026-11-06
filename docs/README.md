# qqbotsdk 文档

QQ 官方机器人 SDK（Python 3.12+）。三个发行包共享 `qqbotsdk` 命名空间，可任意组合安装。

| 包 | 内容 |
|---|---|
| `qqbotsdk-base-py` | 模型基类、共享消息模型、鉴权与 HTTP 会话、`qqbotsdk.ws` 网关客户端 |
| `qqbotsdk-py` | 群聊 / 单聊 / 素材 / 互动 / 菜单 / 面板 + 上层框架 `qqbotsdk.app` |
| `qqbotsdk-guild-py` | 频道域：guild / channel / 成员 / 身份组 / 公告 / 精华 / 日程 / 论坛 / 私信 |

## 安装

```bash
pip install qqbotsdk-py                # 核心
pip install qqbotsdk-guild-py          # 只要频道
pip install "qqbotsdk-py[guild]"       # 核心 + 频道
```

## 配置凭证

项目根目录 `.env`（或环境变量）：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret
TIMEOUT=5000          # 可选，HTTP 超时（毫秒）
```

## 五分钟上手

```python
from qqbotsdk.app import Bot, Context

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    await ctx.reply(f"收到：{ctx.event.content}")


bot.run()
```

## 文档索引

| 文档 | 内容 |
|---|---|
| [auth.md](auth.md) | 凭证获取、缓存与刷新，请求头注入 |
| [app.md](app.md) | 上层框架：监听、分发、注入、中间件、快捷调用 |
| [events.md](events.md) | 事件订阅（intents）与 56 个事件模型 |
| [api.md](api.md) | API 层（薄映射）调用方式、分页、上传，含**全部 105 个接口**的分域索引 |
| [api/auth.md](api/auth.md) | 凭证获取/刷新、`session`、429 重试、统一错误检查、网关地址 |
| [api/bot.md](api/bot.md) | `get_gateway` / `get_me` / `generate_url_link` |
| [api/group.md](api/group.md) | 群消息、富媒体上传、成员、禁言、黑名单、入群审批、自动审批策略 |
| [api/user.md](api/user.md) | 单聊消息、流式消息、富媒体上传 |
| [api/media.md](api/media.md) | 图片素材 prepare / 直传 / complete / 列表 / 删除 |
| [api/menu-panel.md](api/menu-panel.md) | 全局自定义菜单、指令面板 |
| [api/interaction.md](api/interaction.md) | 互动回包与 `code` 取值 |
| [api/guild.md](api/guild.md) | 频道、子频道、成员、身份组、消息、表情表态、公告、精华、日程、论坛、私信、音频 |
| [ws.md](ws.md) | 底层网关客户端：心跳、重连、Resume、关闭码 |
| [errors.md](errors.md) | 三级错误体系、429 重试、错误码排查 |
| [migration-2.0.md](migration-2.0.md) | **0.x / 1.x → 2.x 迁移指南**：逐条代码对照 |
| [examples.md](examples.md) | 可直接运行的示例清单 |

## 目录分层

```
qqbotsdk.app      上层框架（业务方日常只碰这一层）
qqbotsdk.ws       网关客户端（原始帧、回调）
qqbotsdk.api      HTTP 接口薄映射（一接口一函数）
qqbotsdk.model    请求/响应/事件模型
qqbotsdk.errors   三级异常
```

API 层刻意只做两件事：**协议 1:1 映射** 与 **统一错误**。调用便利交给 `qqbotsdk.app`。
