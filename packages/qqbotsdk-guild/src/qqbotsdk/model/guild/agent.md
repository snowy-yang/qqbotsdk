# agent.md — qqbotsdk/model/guild（频道域模型与事件）

适用范围：`packages/qqbotsdk-guild/src/qqbotsdk/model/guild/**`（`channel.py`、`guild.py`、`member.py`、`messages.py`、`content.py`，以及 `event.py`、`event_message.py`、`event_member.py`、`event_forum.py`、`event_audio.py`）。

## MUST（必须做）

- MUST 优先复用已有对象模型（`Guild`、`Channel`、`Member`、`User`、`Role`、`MessageEmbed`、`MessageArk`、`MessageAuthor`），事件体里出现这些对象时直接引用，不要复制字段。
- MUST 对**需要容错**的字段保持 `int`/`str`：`Channel.type` / `sub_type` / `private_type` / `speak_permission`，以及事件里的 `channel_type`（文档 `2=音视频`、`5=直播` 与 `10005` 两处冲突）。在 `description` 里列出取值，不要用 `Literal` 关死。
- MUST 对封闭枚举用 `Literal`：`announces_type`（0/1）、`AudioControlRequest.status`（0-3）、`PutChannelThreadRequest.format`（1-4）、`RemoveGuildMemberRequest.delete_history_msg_days`（-1/0/3/7/15/30）。
- MUST 在事件模型里只建模事件体 `d`，并维护 `EVENT_MODELS` + `parse_event(payload)`（契约见 `qqbotsdk/src/qqbotsdk/model/event/agent.md`）；新增事件必须同时更新注册表与 `__all__`。
- MUST 用 `BeforeValidator` 之类把示例里的**整型 ID 归一化为字符串**（`guild_id`/`channel_id`/`author_id`/`emoji_info.id` 等），保证文档示例与真实报文都能解析。
- MUST 给分页参数加边界：`limit` 的 `le=100`（频道列表）/`le=400`（成员与身份组成员）。

## SHOULD（应当做）

- SHOULD 让响应模型的字段默认可选；频道文档的「返回包」示例比字段表更全时，以示例为准补充可选字段（如 `tts`/`pinned`/`type`/`flags`）。
- SHOULD 用 `EventMessage` 这类继承自响应模型的子类承载事件专有字段（`member`、`mentions`、`seq`），而不是把事件字段塞回响应模型。
- SHOULD 让论坛富文本按 `RichObject` 数组建模（`EventThreadInfo` 等）；表格里写 `string` 而示例是数组时，以示例为准并在说明里注明。

## MUST NOT（禁止做）

- MUST NOT 加回子频道公告相关模型（官方已废弃）。
- MUST NOT 用 `Literal` 收窄 `Channel.type` 这类需要向前兼容的字段。
- MUST NOT 让事件模型继承字段类型不兼容的父类（pyright strict 会报 `reportIncompatibleVariableOverride`）；需要覆盖时新建独立模型。
- MUST NOT 在事件模型里放业务逻辑或发消息。
- MUST NOT 在 `EventMessage` 之外重复定义消息/用户/成员结构。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk-guild\src\qqbotsdk\model
.venv\Scripts\pyright.exe
```

事件回归：每个事件文档页的示例 `d` 先直接 `model_validate`，再包成整帧走 `GatewayPayload` → `parse_event`，两路都断言字段值；并断言 `EVENT_MODELS` 与官方 intents 清单一致（当前 40 个）。
