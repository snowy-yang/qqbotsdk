# 音频与论坛 API（私域）

音频接口仅音频类机器人可用（需联系平台开通）；论坛仅论坛子频道，发帖/删帖为异步任务（返回 `task_id`，结果经 FORUM_* 事件推送，见[事件 payload](/docs/api/events.md)）。

常量：`AUDIO_STATUS_START=0`/`PAUSE=1`/`RESUME=2`/`STOP=3`；`FORUM_FORMAT_TEXT=1`/`HTML=2`/`MARKDOWN=3`/`JSON=4`。

| 方法 | 端点 | 说明 |
|---|---|---|
| `control_channel_audio(channel_id, audio_url=None, text=None, status=AUDIO_STATUS_START)` | POST /channels/{channel_id}/audio | 播放控制（START/PAUSE/RESUME/STOP）；`audio_url`/`text` 仅 START 时传 |
| `put_channel_mic(channel_id)` / `delete_channel_mic(channel_id)` | PUT / DELETE /channels/{channel_id}/mic | 机器人上麦 / 下麦 |
| `get_channel_threads(channel_id)` | GET /channels/{channel_id}/threads | 帖子列表 `{"threads", "is_finish"}` |
| `get_channel_thread(channel_id, thread_id)` | GET …/threads/{thread_id} | 帖子详情 |
| `put_channel_thread(channel_id, title, content, format=FORUM_FORMAT_TEXT)` | PUT /channels/{channel_id}/threads | 发帖，`format` 为 FORUM_FORMAT_* 常量；返回 `task_id` |
| `delete_channel_thread(channel_id, thread_id)` | DELETE …/threads/{thread_id} | 删帖，返回 `task_id` |
