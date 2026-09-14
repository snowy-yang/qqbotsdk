# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

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
