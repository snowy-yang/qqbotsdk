"""事件对象：业务事件推送信封（op/t/d/id）的轻量封装，供 handler 参数注入使用。

事件体字段经 `.typed`（dataclass 解析，见 payloads.py）或 `.data`/`.raw`
访问；被动回复凭据分两类——消息事件用事件体里的 id（payload 的 `id`
字段），其余事件用信封顶层的 `.event_id`。
"""

from typing import Any

from .model import Payload
from .payloads import parse_event


class Event:
    """一条业务事件（op=0）的推送信封；只封装信封语义，不做字段名映射。"""

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
    def event_id(self) -> str | None:
        """推送信封顶层的事件 id（与 op/t/d 平级）。

        非消息事件（GROUP_ADD_ROBOT 等）事件体里没有 id，被动回复的
        event_id 只有这里能拿到；消息事件的被动回复凭据是事件体里的
        id（payload 的 `id` 字段，即 msg_id），别取这里的信封 id。
        """
        id_ = self._payload.get("id")
        return id_ if isinstance(id_, str) else None

    def __repr__(self) -> str:
        return f"<Event {self.type} {self._d}>"
