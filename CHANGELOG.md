# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- Markdown 与内嵌按钮一等支持：`post_group_message`/`post_c2c_message` 新增 `markdown`/`keyboard` 参数（自动置 msg_type=2，与 content 互斥）；新增 `respond_interaction()` 回应按钮回调；`Interaction` payload 补齐 `chat_type`/`scene`/`group_openid` 等官方字段
- `Event` 新增 `event_id` 属性（推送信封顶层的事件 id，与 op/t/d 平级）：非消息事件（GROUP_ADD_ROBOT 等）的被动回复不再需要手动 `event.raw["id"]`
- 按钮快捷构造与点击处理：`button()`/`keyboard()` 生成内嵌按钮（免手写嵌套 dict）；`Interaction` 新增 `button_data` 属性（被点按钮的 action.data）；examples/group_bot 补 `/btn` 卡片与 `INTERACTION_CREATE` 回调示例
- 文档站点：基于 docsify（侧边栏、全文搜索、代码复制、mermaid 图渲染、分页），`npx docsify-cli serve` 本地预览；新增 `examples/README.md` 示例索引

### 变更

- **移除 dishka 依赖，改为内置参数注入**：handler 形参直接标注组件类型（`api: BotApi`）即注入，不再需要 `Inject[T]` 包装；组件改在 `run_loop` 显式装配并按类型登记到 `emitter.services`（自定义组件同样登记即可注入）。破坏性变更：`Inject`、`make_container`、`use_container` 随之移除，原 `api: Inject[BotApi]` 写法改为 `api: BotApi`

### 移除

- 音乐插件示例（`plugins/`、根目录 `main.py`）已拆分为独立的点歌 bot 项目（含 Markdown 卡片、按钮回调与内置短网址多线程下载代理），不再随 SDK 仓库分发

### 修复

- token 请求失败时抛出 `TokenError`（携带 QQ 返回的 `code`/`message`），不再抛出掩盖真实原因的 `KeyError: 'access_token'`
- 修正被动回复 `event_id` 的指引：官方要求取网关帧最外层的 id（`Event.event_id`），事件体里的裸 UUID（`Interaction.id` 等）不能作 `event_id`，此前文档与 docstring 的说法有误
- 响应 `Content-Type` 非 JSON 时不再抛 `ContentTypeError`（个别接口如回应互动返回 200 text/plain + `{}` body）；JSON 解析统一切换 ujson

## [0.1.0] - 2026-09-14

首个公开版本：QQ 官方机器人 Python SDK（Python 3.13 / asyncio / aiohttp）。

### 新增

- **双接入方式**：WebSocket 长连接与 Webhook HTTP 回调，由 `.env` 的 `CONNECTER` 切换，handler 写法完全一致
- **协议层**：HELLO 鉴权（IDENTIFY/RESUME 自动切换）、apscheduler 定时心跳、READY 会话捕获、INVALID_SESSION 处理；断线指数退避重连 + 心跳/静默双看门狗，重连自动 RESUME 续传
- **Webhook**：Ed25519 验签、op=13 验证请求自动应答、60s TTL 事件去重
- **事件分发**：`EventEmitter` 按 op/t 名路由，payload dataclass 类型化参数、`Event` 封装与 dishka 依赖注入（`Inject[T]`）三种 handler 写法，异常就地隔离
- **事件订阅**：`intents.toml` 声明式控制订阅掩码
- **业务 API**（`BotApi`）：v2 群/单聊消息收发与撤回、富媒体上传、群禁言；频道消息/表态/撤回、公告、精华、日程、频道禁言、频道与成员信息查询；HTTP ≥400 统一抛 `ApiError`
- **文档**：使用指南、API 参考、架构说明与可运行示例（`examples/`）
- **测试**：纯逻辑单测 + 假网关 WebSocket 端到端 + Webhook 验签/去重端到端

[0.1.0]: https://gitea.4i.hk/hhhge/qqbotsdk/releases/tag/v0.1.0
