# agent.md — 仓库总则

适用范围：整个仓库（`packages/**`）。子模块的规定见各自目录下的 `agent.md`，冲突时**就近优先**。

依赖方向（单向，不可违反）：`qqbotsdk-base-py` ← `qqbotsdk-py` ← （可选）`qqbotsdk-guild-py`。

## MUST（必须做）

- MUST 动手前先读：目标文件、同目录其它文件、本目录及上级目录的 `agent.md`；再决定改什么。
- MUST 保持「1:1 HTTP 薄映射」：一个接口 = 一个 `async def`，路径参数外置，请求体 `payload: XxxRequest`，返回 `XxxResponse`。
- MUST 让所有请求体走 `payload.model_dump(exclude_none=True)`，无响应体的接口返回 `None`。
- MUST 改完后跑通质量门（全部为零错误）：

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\pyright.exe          # strict，已通过 venvPath/venv 指向 .venv
```

- MUST 注释与 docstring 使用 ASCII 标点（`,` `:` `(` `)` `;`），否则 ruff 的 RUF002/RUF003 会报错；只有字符串字面量（`description=`、日志文案）可以用全角中文标点。
- MUST 让 `__all__` 按 isort 风格排序（ruff RUF022 会拦）。
- MUST 给所有函数、方法、变量完整类型注解（pyright strict + `reportMissingParameterType`）。
- MUST 用 `read`/`edit`/`write` 工具改文件；中文内容用 PowerShell 写会破坏 UTF-8 编码。

## SHOULD（应当做）

- SHOULD 最小改动：只碰完成任务必需的代码，不做顺手重构、不批量重排无关行。
- SHOULD 用官方文档的示例 JSON 当测试数据来验证模型；断言具体字段值，而不是「不报错即通过」。
- SHOULD 新增模型前先 grep 是否已有可复用对象（`Guild`/`Channel`/`Member`/`User`/`Message*` 等）。
- SHOULD 把临时脚本放在 `$env:TEMP`，跑完删除，不留在仓库里。
- SHOULD 改了公开 API 就同步文档与示例：`docs/`（简单 md）与 `examples/`（可运行脚本），两者都要能被 ruff 格式化通过。

## MUST NOT（禁止做）

- MUST NOT 违反依赖方向：`base` 包不得 import `qqbotsdk-py` 或 `qqbotsdk-guild-py`；`qqbotsdk-py` 不得 import guild 包（guild 是 optional extra，反向 import 会让裸装失败）。
- MUST NOT 建模官方标注**【已废弃】**或已确认不可用的字段与接口，历史决策示例：`Keyboard.id`（内嵌键盘模板）、`MessageMarkdown.template_id`/`custom_template_id`（群/单聊侧）、`Action.click_limit`、子频道公告 `post/delete_channel_announces`。
- MUST NOT 实现分片（LoadBalance）：网关固定单连接、`Identify` 恒为 `shard=[0, 1]`；`GET /gateway/bot` 不封装。
- MUST NOT 重命名或删除公开类/函数（跨包被 import，属破坏性变更）；确需变更必须先取得明确许可。
- MUST NOT 在日志、异常信息、测试输出里打印 `APPSECRET`、`access_token` 或其它凭证；`.env` 不入库（已在 `.gitignore`）。
- MUST NOT 在多人/多 agent 并行写同一仓库时跑 `ruff format .`（会重排别人正在编辑的文件）；只格式化自己改过的文件。
- MUST NOT `git add` / `git commit` / `git push`，除非被明确要求。
- MUST NOT 把 `.env` 里的真实凭证写进源码、注释、文档或测试。

## 错误与重试约定（MUST）

- MUST 只用 `qqbotsdk.errors` 的三级异常：`QQBotAPIError`（HTTP 与业务错误码）、`QQBotAuthError`（凭证）、`QQBotGatewayError`（网关）。新增异常必须继承 `QQBotError`。
- MUST 让错误检查集中在 `api/core.py` 的 `response_class` 里，**不许**在 99 个 api 函数里重复写 `if resp.status == ...`。
- MUST 只在 HTTP 429 上自动重试（最多 3 次、优先 `Retry-After`、指数退避 + 抖动、总等待 ≤ 30 秒）；429 代表请求未被处理，因此 POST 也可重试。
- MUST 让错误信息带上 `trace_id`（头 `X-Tps-trace-ID`，回退 body 的 `trace_id`）。
- MUST NOT 吞异常：`except` 之后要么重新抛，要么记 `logger.exception`。

## 分层与聚合约定（MUST）

- MUST 让 API 层保持「薄映射 + 统一错误」两件事；调用便利、事件监听、分发、注入、快速调用一律放上层 `qqbotsdk.app`，**不许**在 api 层加半吊子封装（用户明确决策：api 层不承担降低调用成本）。
- MUST NOT 在 `qqbotsdk/`、`qqbotsdk/api/`、`qqbotsdk/model/` 这三个**命名空间包顶层目录**加 `__init__.py`：`qqbotsdk` 由三个发行包共用，加常规包会让 pyright 只认本包目录，`model.core` / `api.core` 全部解析失败（实测连锁 1400+ errors）。子包（如 `qqbotsdk/ws/`、`qqbotsdk/app/`）可以有 `__init__.py`。
- MUST 让 `ws.on()` 的 handler 与 app 层的 handler 都通过独立任务派发，绝不阻塞收包循环；并且注册回调后 `async for` 仍须可用。
- MUST 让 handler 的异常只记日志或交给 `on_error` 兜底，不外抛（一个回调崩掉不能影响连接）。
