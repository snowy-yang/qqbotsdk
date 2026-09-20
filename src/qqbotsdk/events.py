"""事件对象：对线上 payload 的轻量封装，供业务 handler 经 DI 注入使用。"""

from typing import Any

from .model import Payload
from .payloads import parse_event


class Event:
    """一条业务事件（op=0）；属性取值兼容群（openid）与频道两套字段名。"""

    def __init__(self, payload: Payload) -> None:
        self._payload = payload
        t = payload.get("t")
        self.type: str | None = t if isinstance(t, str) else None
        self._d: dict[str, Any] | None = None
        self._typed: object | None = None

    @property
    def raw(self) -> Payload:
        return self._payload

    @property
    def data(self) -> dict[str, Any]:
        """d 的只读副本；仅用到 `.typed`/`.raw` 的 handler 不会触发这次拷贝。"""
        if self._d is None:
            d = self._payload.get("d")
            self._d = dict(d) if isinstance(d, dict) else {}
        return self._d

    @property
    def typed(self) -> object:
        """d 的 dataclass 解析结果（见 payloads.py）；未知事件类型为 dict。"""
        if self._typed is None:
            self._typed = parse_event(self.type, self.data)
        return self._typed

    @property
    def user_id(self) -> str | None:
        return self.data.get("user_id") or self.data.get("from_user_id")

    @property
    def group_id(self) -> str | None:
        return self.data.get("group_openid")

    @property
    def content(self) -> str | None:
        return self.data.get("content")

    @property
    def message_id(self) -> str | None:
        return self.data.get("id")

    @property
    def event_id(self) -> str | None:
        """推送信封顶层的事件 id（与 op/t/d 平级）。

        非消息事件（GROUP_ADD_ROBOT 等）事件体里没有 id，被动回复的
        event_id 只有这里能拿到；消息事件用 `.message_id`（即 msg_id）。
        """
        id_ = self._payload.get("id")
        return id_ if isinstance(id_, str) else None

    def __repr__(self) -> str:
        return f"<Event {self.type} {self._d}>"
