# agent.md — qqbotsdk/model/event（群聊/单聊/好友/互动事件模型）

适用范围：`packages/qqbotsdk/src/qqbotsdk/model/event/**`（`__init__.py`、`group.py`、`c2c.py`、`interaction.py`）。

## MUST（必须做）

- MUST 只建模事件体 `d`：**不要**在事件模型里重复 `id`/`op`/`s`/`t`（信封是 `qqbotsdk.ws.payload.GatewayPayload`）。
- MUST 每个域导出一张注册表和一个解析函数，签名固定：

```python
EVENT_MODELS: dict[str, type[QQBotBaseModel]] = {
    "GROUP_AT_MESSAGE_CREATE": GroupAtMessageCreateEvent
}


def parse_event(payload: GatewayPayload) -> QQBotBaseModel | None:
    model = EVENT_MODELS.get(payload.t or "")
    if model is None:
        return None
    return model.model_validate(payload.d)
```

- MUST 用官方事件大写名做 key，类名为 `PascalCase + Event`（如 `GROUP_AT_MESSAGE_CREATE` → `GroupAtMessageCreateEvent`）。
- MUST 让 `parse_event` 对未建模事件、心跳帧、`t` 为空一律返回 `None`，不抛异常。
- MUST 在新增事件时同步更新 `EVENT_MODELS` 与 `__all__`，并用文档示例 JSON 断言关键字段值。

## SHOULD（应当做）

- SHOULD 让结构相同的事件共用基类（`GROUP_AT_MESSAGE_CREATE` 与 `GROUP_MESSAGE_CREATE` 共用 `GroupMessageEventBase`）。
- SHOULD 复用本包已有模型：`GROUP_JOIN_REQUEST` 直接继承 `model/group/join_request.JoinRequest`。
- SHOULD 把群/单聊共用的事件子对象（用户、引用场景、附件、ark 卡片、消息元素）集中在 `group.py`，`c2c.py` 复用。

## MUST NOT（禁止做）

- MUST NOT import `qqbotsdk-guild-py` 的模型：guild 是 optional extra，反向依赖会让裸装 `ImportError`。频道事件模型在 `qqbotsdk.model.guild.event`，由装了 guild 包的调用方自行合并解析。
- MUST NOT 把「接口请求模型」当事件模型复用（例如 `model/interaction.py` 是接口请求，`event/interaction.py` 是事件对象，两者字段不同）。
- MUST NOT 用 `Literal` 收窄 `message_type`、`interaction.type` 这类历史上有额外取值的字段；用 `int` + `description` 列出已知取值。
- MUST NOT 在事件模型里塞业务逻辑（判断、编排、发消息）。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\model\event
.venv\Scripts\pyright.exe
```

回归：把每个事件文档页的示例 `d` 直接 `model_validate`，再包成整帧 `{"id","op":0,"s","t","d"}` 走 `GatewayPayload` → `parse_event`，两条路径都要断言字段值。
