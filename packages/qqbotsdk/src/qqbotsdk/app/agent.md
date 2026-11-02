# agent.md — qqbotsdk/app（上层框架）

适用范围：`packages/qqbotsdk/src/qqbotsdk/app/**`（`__init__.py`、`bot.py`、`context.py`、`dispatch.py`）。

职责：事件监听 / 分发 / 注入 / 中间件 / 快捷调用。**业务方只用这一层**，不用手写分发循环。

## MUST（必须做）

- MUST 让 handler 只接收一个参数：`async def h(ctx: Context) -> bool | None`。不要做成多参数或按名字注入，可预测性优先。
- MUST 把每个 Dispatch 放进独立 `asyncio.Task` 执行，句柄集中保存；`stop()` 必须取消并 `gather` 回收，绝不留残任务。
- MUST 让 handler / 中间件的异常交给 `on_error` 注册的函数；未注册时 `logger.opt(exception=exc).error`。异常**绝不**允许冒泡到 ws 收包循环。
- MUST 保持洋葱语义：先注册的中间件在外层，`await call_next()` 向内，不调用即拦截。
- MUST 保持阻断语义：handler 返回 `False` 时不执行后续 handler，中间件照常收尾。
- MUST 让 `ctx.reply()` 的锚点「事件 ID 优先」：`payload.id` → `event_id`；否则 `d.id` → `msg_id`；两者互斥；都没有返回 `None`（不退化成主动消息）。
- MUST 让 `msg_seq` 按锚点自增（LRU 上限 512），显式传入则覆盖并把计数推进到该值。
- MUST 用 `qqbotsdk.errors` 的异常体系做错误分类，不在本层发明新异常。
- MUST 在事件解析上惰性降级 guild：`importlib.util.find_spec("qqbotsdk.model.guild.event")` + 函数内 import，解析失败把 `ctx.event` 置 `None` 并记日志。

## ctx.api（SceneApi）约定（MUST）

- MUST 让 `send*` 系列只发**主动消息**（不带 `event_id` / `msg_id` / `msg_seq`）；被动回复必须走 `reply()` 并委托 `Context.reply()`，不许重复实现锚点与 msg_seq。
- MUST 按场景路由：`d.group_openid` → `group`；`d.author.user_openid` 或事件体顶层 `d.openid`（`FRIEND_ADD`、`C2C_MSG_RECEIVE` 等）→ `c2c`；都没有 → `other` 并抛 `ValueError`。
- MUST 让 `upload_image` 先算 `md5` / `sha1` / 前 10002432 字节的 `md5`，按响应里的 `parts`（**顶层字段**，按 `index` 排序）逐片 PUT，再 finish、合并取 `file_info`。
- MUST 让 `approve_join_request` / `decline_join_request` 只在群聊场景可用，`member_openid` 省略时从事件体取，取不到抛 `ValueError`。
- MUST 让 `ack_interaction` 只在 `INTERACTION_CREATE` 事件里可用，`interaction_id` 取 `d.id` 并剥离可能的 `INTERACTION_CREATE:` 前缀，`code` 走 `Literal[0..5]` 校验。
- MUST NOT 在 `SceneApi` 里新增业务逻辑或缓存消息状态（除了 `ctx.reply` 的 msg_seq 计数在 `Bot` 里）。
- MUST NOT 声称支持「好友申请审核」：QQ 没有该接口，`FRIEND_ADD` 只是通知。

## 键盘助手约定（keyboard.py，MUST）

- MUST 让 `callback` / `link` / `command` 只返回 `Button`，不自行组装 `Row`；`row` 负责行、`keyboard` / `KeyboardBuilder` 负责整体。
- MUST 在**组装阶段**统一分配缺失的 `button_id`（`btn-1`、`btn-2`…，同一键盘内唯一），不要在 helper 里用全局计数器。
- MUST 校验官方上限：最多 5 行、每行最多 5 个按钮，超限抛 `ValueError`；`link` 的 URL 必须 `https://`。
- MUST 用 `model_validate({...})` 拼装 pydantic 模型，**不要**用部分关键字构造（`Field(default=None)` 之前 pyright 会误判必填）。
- MUST NOT 把样式以外的业务规则（权限、可见性）写进 helper：权限用 `Permission` 模型透传。
- MUST 让权限语法糖（`everyone` / `only_admin` / `only_users` / `only_roles`）只做 `Permission` 工厂，与其文档里的显式写法 1:1 等价、不改任何默认值、空参数抛 `ValueError`；并同步导出到 `qqbotsdk.app` 的 `__all__`（设计标准见 `docs/syntactic-sugar.md`）。

## SHOULD（应当做）

- SHOULD 让 `ctx.state` 作为中间件与 handler 的共享通道（例如鉴权结果、开始时间）。
- SHOULD 让日志带事件名与 `event_id`，方便和 `trace_id` 对齐排查。
- SHOULD 保持 `Bot.on_message()` / `on_ready()` / `on_error()` 的「工厂式」用法（`@bot.on_message()`），`@bot.middleware` 是直接装饰器。

## MUST NOT（禁止做）

- MUST NOT 在本层写业务逻辑或调用具体业务接口（发消息走 `ctx.reply` / `ctx.send`，其它用 `ctx.bot` 暴露的底层能力）。
- MUST NOT 在模块顶层 import `qqbotsdk-guild-py`（optional extra）。
- MUST NOT 在 handler 里做长耗时阻塞调用（`time.sleep`、同步 IO），会拖垮事件处理。
- MUST NOT 让 `stop()` 取消当前正在执行的任务（在 handler 内调用 `await bot.stop()` 必须安全）。
- MUST NOT 打印 token 或凭证。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\app tests
.venv\Scripts\pyright.exe
.venv\Scripts\python.exe -m pytest tests/test_app.py -q
```

回归方式：本地 `aiohttp.web` 假网关（Hello → Identify → READY → Dispatch → 关闭），验证注册顺序、中间件洋葱、阻断、异常进 `on_error`、`ctx.reply` 的锚点与 `msg_seq`、`stop()` 清理。
