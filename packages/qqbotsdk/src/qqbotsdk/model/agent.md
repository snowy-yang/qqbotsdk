# agent.md — qqbotsdk/model（顶层请求/响应模型）

适用范围：`packages/qqbotsdk/src/qqbotsdk/model/*.py`（`bot.py`、`interaction.py`、`media.py`、`menu.py`、`panel.py`）。
子目录 `group/`、`user/`、`event/` 各有自己的 `agent.md`。

## MUST（必须做）

- MUST 继承 `QQBotBaseModel`，字段写法遵守 `packages/qqbotsdk-base/src/qqbotsdk/model/agent.md`（多行 `Field`、中文 description、必填 `Field(...)`）。
- MUST 与 `api/` 一一对应：一个接口的请求/响应各一个模型，命名 `XxxRequest` / `XxxResponse`。
- MUST 让**响应模型**的字段默认可选（`| None = Field(default=None, ...)`），只有文档明确「总是返回」时才必填。
- MUST 对封闭枚举用 `Literal[...]`（如 `PanelRecord.scope`、`MenuItem.type`），并在 `description` 里列出取值含义。
- MUST 在改动后跑全仓质量门（这些模型被 api 层直接依赖）。

## SHOULD（应当做）

- SHOULD 对分页参数加 `le`/`ge`（如 `limit` 的 `le=50`），对数量上限加 `max_length`。
- SHOULD 复用 `qqbotsdk-base` 的共享子模型（`MessageCard`、`Keyboard`、`MessageMarkdown`、`UploadPrepareResponse`）。

## MUST NOT（禁止做）

- MUST NOT 在顶层模型里定义属于群域/单聊域的结构——放到 `group/`、`user/`。
- MUST NOT 把路径参数（`user_openid`、`panel_id`）写进请求体模型。
- MUST NOT 用 `str` 兜住本该枚举的字段（会给调用方埋坑）；但**响应**里取值可能扩充的字段（如 `message_type`）保持 `int`/`str` 并在说明里列出取值。
- MUST NOT 建模官方标注【已废弃】的字段。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\model
.venv\Scripts\pyright.exe
```
