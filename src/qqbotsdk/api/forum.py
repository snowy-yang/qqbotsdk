"""论坛方法集（私域，仅论坛子频道）：帖子列表、详情、发帖与删帖。

发帖/删帖为异步任务（返回 task_id），结果经 FORUM_* 事件推送；
content 为 FORMAT_JSON 时参照官方 RichText 结构。仅私域机器人可用。
"""

from typing import Any

from .core import BaseApi

# 帖子内容格式（format）
FORUM_FORMAT_TEXT = 1
FORUM_FORMAT_HTML = 2
FORUM_FORMAT_MARKDOWN = 3
FORUM_FORMAT_JSON = 4


class ForumApi(BaseApi):
    """论坛方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    async def get_channel_threads(self, channel_id: str) -> dict:
        """获取帖子列表（GET /channels/{channel_id}/threads）。

        返回 {"threads": [...], "is_finish": ...}（1 表示已拉取完毕）；
        threads 内 content 为 RichText 结构。
        """
        return await self.get(f"/channels/{channel_id}/threads")

    async def get_channel_thread(self, channel_id: str, thread_id: str) -> dict:
        """获取帖子详情（GET .../threads/{thread_id}），含首楼与回复。"""
        return await self.get(f"/channels/{channel_id}/threads/{thread_id}")

    async def put_channel_thread(
        self,
        channel_id: str,
        title: str,
        content: str,
        format: int = FORUM_FORMAT_TEXT,
        **extra: Any,
    ) -> dict:
        """发表帖子（PUT /channels/{channel_id}/threads）。

        format 为 FORUM_FORMAT_* 常量；返回 {"task_id": ...}，发表结果
        经 FORUM_THREAD_CREATE 事件推送。
        """
        body: dict[str, Any] = {
            "title": title,
            "content": content,
            "format": format,
        }
        body.update(extra)
        return await self.put(f"/channels/{channel_id}/threads", json=body)

    async def delete_channel_thread(self, channel_id: str, thread_id: str) -> dict:
        """删除帖子（DELETE .../threads/{thread_id}）。

        返回 {"task_id": ...}，删除结果经 FORUM_THREAD_DELETE 事件推送。
        """
        return await self.delete(f"/channels/{channel_id}/threads/{thread_id}")
