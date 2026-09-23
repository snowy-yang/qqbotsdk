"""音频方法集（仅音频类机器人）：子频道播放控制与上/下麦。

需联系平台开通权限后调用；控制与上/下麦均触发 AUDIO_ACTION 事件。
"""

from typing import Any

from .core import BaseApi

# 播放状态（AudioControl.status）
AUDIO_STATUS_START = 0
AUDIO_STATUS_PAUSE = 1
AUDIO_STATUS_RESUME = 2
AUDIO_STATUS_STOP = 3


class AudioApi(BaseApi):
    """音频方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    async def control_channel_audio(
        self,
        channel_id: str,
        audio_url: str | None = None,
        text: str | None = None,
        status: int = AUDIO_STATUS_START,
    ) -> dict:
        """控制子频道音频播放（POST /channels/{channel_id}/audio）。

        status 为 START/PAUSE/RESUME/STOP（AUDIO_STATUS_* 常量）；
        audio_url 与状态文本 text 仅 START 时传。
        """
        body: dict[str, Any] = {"status": status}
        if audio_url is not None:
            body["audio_url"] = audio_url
        if text is not None:
            body["text"] = text
        return await self.post(f"/channels/{channel_id}/audio", json=body)

    async def put_channel_mic(self, channel_id: str) -> dict:
        """机器人上麦（PUT /channels/{channel_id}/mic）。"""
        return await self.put(f"/channels/{channel_id}/mic")

    async def delete_channel_mic(self, channel_id: str) -> dict:
        """机器人下麦（DELETE /channels/{channel_id}/mic）。"""
        return await self.delete(f"/channels/{channel_id}/mic")
