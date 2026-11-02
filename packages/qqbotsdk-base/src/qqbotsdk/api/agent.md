# agent.md — qqbotsdk-base/api（HTTP 会话与鉴权）

适用范围：`packages/qqbotsdk-base/src/qqbotsdk/api/**`（`core.py`、`auth.py`）。

职责：让所有业务包「不带任何鉴权代码」也能直接调用 OpenAPI。

## MUST（必须做）

- MUST 让 `session` 保持**懒加载单例**：首次使用时才创建 `aiohttp.ClientSession`；`import` 阶段不得触碰事件循环。
- MUST 通过 `TraceConfig.on_request_start` 统一注入 `Authorization: QQBot <access_token>`，业务函数不得手写该请求头。
- MUST 只对 `https://api.bot.qq.com` 的请求注入鉴权头：
  - 发往其它域名的绝对地址（COS 预签名上传）MUST NOT 带；
  - `/app/getAppAccessToken` 本身 MUST NOT 带。
- MUST 在换取 token 时按**响应体 `code`** 判定失败（该接口业务错误仍返回 HTTP 200），失败抛 `QQBotAuthError`。
- MUST 容忍 `expires_in` 为字符串（官方示例是 `"7200"`）。
- MUST 在剩余有效期不足 60 秒时主动刷新，并用 `asyncio.Lock` 保证并发只换取一次。

## SHOULD（应当做）

- SHOULD 保持 `get_access_token()` / `get_authorization()` / `reset_access_token()` 三个公开入口的签名稳定。
- SHOULD 让超时来自环境变量 `TIMEOUT`（毫秒，缺省 5000），便于部署调整。
- SHOULD 提供 `session.client` 暴露底层 `ClientSession`，供 `ws` 等需要原生能力的场景使用。

## MUST NOT（禁止做）

- MUST NOT 在 `core.py` 里写业务接口逻辑；它只负责会话、请求头、错误面。
- MUST NOT 缓存到磁盘或用全局可变状态以外的机制持久化 token。
- MUST NOT 允许「无凭证时 import 就报错」：缺少 `APPID`/`APPSECRET` 只能在实际换取 token 时报错。
- MUST NOT 把 token 写进日志、异常 message 或 `repr`；需要标识时只打印长度或前几位掩码。
- MUST NOT 修改 `session` 的公开用法（`async with session.get(...) as resp`），否则 20+ 个业务模块会全部失效。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk-base\src\qqbotsdk\api
.venv\Scripts\pyright.exe
```

联调：`QQBOT` 凭证配置好后，`await get_me()` 应能返回机器人信息；注入假 token 时应得到 HTTP 401（说明头已注入）。
