# agent.md — qqbotsdk-base/model（基类与共享子模型）

适用范围：`packages/qqbotsdk-base/src/qqbotsdk/model/**`（`core.py`、`sub/messages.py`、`sub/upload.py`）。

## MUST（必须做）

- MUST 让所有模型继承 `QQBotBaseModel`（已配置 `validate_by_name`、`serialize_by_alias`、`extra="allow"`）；禁止直接继承 `pydantic.BaseModel`。
- MUST 用「字段名 + 多行 `Field`」的固定写法，尾逗号：

```python
msg_type: Literal[0, 2, 7, 8] | None = Field(
    default=None,
    description="消息类型：0=纯文本，2=Markdown，7=富媒体，8=图文卡片",
)
required_name: str = Field(
    ...,
    description="必填字段用省略号",
)
```

- MUST 可选字段写成 `Field(default=None, ...)` 而不是 `Field(None, ...)`：pydantic 2.14 + pyright 会把后者当成必填，导致用户侧任何「部分构造」（如 `SendGroupMessagesRequest(content="x")`）都报 `reportCallIssue`。
- MUST 严格照文档定必填性：「必填=是」→ `Field(...)`；「必填=否」→ `Field(default=None, ...)`。
- MUST 让 `description` 用中文、单句、**不加结尾句号**，并尽量沿用文档原词。
- MUST 在收紧取值时用 `Literal[...]`，在有明确上下限时加 `ge`/`le`/`max_length`/`min_length`。
- MUST 保持向后兼容：只允许新增字段、放宽类型、改描述；删除/改名/收窄公开字段前必须取得许可。

## SHOULD（应当做）

- SHOULD 把「多业务域共用」的结构放这里（键盘、Markdown、引用、富媒体、卡片、分片上传）；单一业务域专有的模型放各自包。
- SHOULD 用 `list[X] | None` 而不是 `list[X] = []`；需要可变默认值时用 `Field(default_factory=list)`。
- SHOULD 用 `RootModel` 表达「裸数组」响应，用普通模型表达对象响应。

## MUST NOT（禁止做）

- MUST NOT 建模已废弃/不可用字段：`Keyboard.id`（内嵌键盘模板）、群/单聊 `MessageMarkdown.template_id` / `custom_template_id`、`Action.click_limit`、`Action.at_bot_show_channel_list`。
- MUST NOT 按「码点」加中文字符数上限——文档说「一个中文汉字算 2 个字符」时，把限制写进 `description`，不要加 `max_length`（会比文档更严，误拒合法输入）。
- MUST NOT 在这里 import 任何业务包（`qqbotsdk.model.group` / `guild` / `event` 等）。
- MUST NOT 为同一个结构重复造多个类；共享子模型只有一个定义。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk-base\src\qqbotsdk\model
.venv\Scripts\pyright.exe
```

改动的字段会影响 `qqbotsdk-py` 与 `qqbotsdk-guild-py` 的所有请求模型，改完必须全仓跑质量门。
