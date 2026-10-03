# 收发消息

被动回复规则、主动消息、富媒体、Markdown 按钮与撤回。各 API 的完整参数见 [API 参考](/docs/api/v2.md)。

## 被动回复（最常用）

携带 `msg_id`（回复某条消息）或 `event_id`（响应某类事件，二选一）即为被动回复，**不需要任何消息频率白名单**。两个 id 来源不同：`msg_id` 是消息事件体里的 `d.id`；`event_id` 是**网关推送最外层**的 id（`event.event_id`，形如 `INTERACTION_CREATE:uuid`），不是事件体里的裸 UUID：

- 群聊：收到消息后 **5 分钟**内可回复，同一 `msg_id` 最多 **5 次**；
- 单聊：**60 分钟**内可回复，同一 `msg_id` 最多 **4 次**；
- 同一条消息多次回复必须递增 `msg_seq`（相同 `msg_id`+`msg_seq` 会发送失败）；
- 被动回复同样受内容审核。

```python
await api.post_group_message(
    group_openid, content="你好", msg_id=msg.id, msg_seq=1,
)
```

非消息事件（入群 `GROUP_ADD_ROBOT`、按钮回调 `INTERACTION_CREATE` 等）的被动回复凭据只能取 `event.event_id`（信封顶层 id）：

```python
@bot.on("GROUP_ADD_ROBOT")
async def on_added(added: GroupAddRobot, event: Event, api: BotApi):
    await api.post_group_message(
        added.group_openid, content="大家好～", event_id=event.event_id,
    )
```

## 主动消息

不带 `msg_id`/`event_id` 即主动消息，有额外频控（群/单聊每日每对象 1000 条），且默认关闭，需在开放平台申请。用户可在资料卡关闭主动推送（对应 `C2C_MSG_REJECT`/`GROUP_MSG_REJECT` 事件，关闭后发送会失败）。

## 富媒体（图片/视频/语音/文件）

先上传拿 `file_info`，再作为 `media` 发送（此时 SDK 自动把 `msg_type` 置为 7，`content` 作媒体下方的文字）：

```python
upload = await api.upload_group_file(
    group_openid, file_type=1, url="https://example.com/pic.png",
)
await api.post_group_message(
    group_openid, content="看图", msg_id=msg.id, media=upload,
)
```

`file_type`：1 图片、2 视频、3 语音、4 文件。也可在 `upload_*_file` 传 `srv_send_msg=True` 让上传即发送。

## Markdown 与按钮（msg_type=2）

`post_group_message`/`post_c2c_message` 直接支持 `markdown=`（字符串或完整 dict，自动 `msg_type=2`，与 `content` 互斥）；`button()`/`keyboard()`（`from qqbotsdk.api import button, keyboard`）构造内嵌按钮：

```python
await api.post_group_message(
    group_openid,
    markdown="## 标题\n**加粗**正文",
    keyboard=keyboard(
        button("点我", data="我的按钮数据"),                 # 单按钮独占一行
        [button("赞", data="like"), button("踩", data="dislike")],  # 列表同行并排
    ),
    msg_id=msg.id,
)
```

- `button(label, data, *, type=1, permission=2, style=1)`：`type` 1 回调（点击推 `INTERACTION_CREATE`）、0 跳转链接（data 为 url）、2 指令（往输入框插入 data）；`permission` 2 所有人 / 1 管理员 / 0 指定用户；`label` 官方限 10 字以内；要补嵌套字段（如 `visited_label`、`prompt`）直接修改返回的 dict。
- 其他 body 字段可经 `**extra` 透传（如原生 `msg_type=6` 输入中状态）。

**处理按钮点击**：点击回调推 `INTERACTION_CREATE` 事件，`inter.button_data` 即被点按钮的 `data`：

```python
@bot.on("INTERACTION_CREATE")
async def on_button(inter: Interaction, event: Event, api: BotApi):
    # 必须应答，否则用户端按钮一直 loading（inter.id 是事件体里的互动 id）
    await api.respond_interaction(inter.id)
    await api.post_group_message(
        inter.group_openid, content=f"你点了：{inter.button_data}",
        event_id=event.event_id,
    )
```

- **`event_id` 要取网关帧最外层的 id（`event.event_id`），不能用事件体里的裸 UUID `inter.id`**——`inter.id` 只用于 `respond_interaction`，这是官方文档点名的常见坑；
- 需要在 intents.toml 开启 `INTERACTION` 分组；
- Markdown 有平台权限要求，无权限时发送会抛 `ApiError`（业务 code 304036/40034127），按需回退纯文本。

## 流式消息（AI 逐段下发）

`post_c2c_stream_message` 把回复拆成多片依次下发（适合 LLM 逐段输出）：首片不传 `stream_msg_id`，响应里的 `id` 即后续分片要携带的值，`index` 从 0 递增，最后以 `input_state=STREAM_FINISHED` 收尾。参数与常量见 [v2 API](/docs/api/v2.md#流式消息)。

## 撤回

- 群/单聊（v2）：发出 **2 分钟**内可撤回（`withdraw_group_message`/`withdraw_c2c_message`）；
- 频道：仅私域机器人可撤回（`withdraw_channel_message`，`hide_tip=True` 隐藏撤回小灰条）。
