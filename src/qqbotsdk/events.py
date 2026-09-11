"""事件对象：对线上 payload 的轻量封装，供业务 handler 经 DI 注入使用。"""

from typing import Any

from .model import Payload
from .payloads import parse_event


class Event:
    """一条 DISPATCH 事件；属性取值兼容群（openid）与频道两套字段名。"""

    def __init__(self, payload: Payload) -> None:
        self._payload = payload
        t = payload.get("t")
        self.type: str | None = t if isinstance(t, str) else None
        d = payload.get("d")
        self._d: dict[str, Any] = dict(d) if isinstance(d, dict) else {}
        self._typed: object | None = None

    @property
    def raw(self) -> Payload:
        return self._payload

    @property
    def data(self) -> dict[str, Any]:
        return self._d

    @property
    def typed(self) -> object:
        """d 的 dataclass 解析结果（见 payloads.py）；未知事件类型为 dict。"""
        if self._typed is None:
            self._typed = parse_event(self.type, self._d)
        return self._typed

    @property
    def user_id(self) -> str | None:
        return self._d.get("user_id") or self._d.get("from_user_id")

    @property
    def group_id(self) -> str | None:
        return self._d.get("group_openid")

    @property
    def content(self) -> str | None:
        return self._d.get("content")

    @property
    def message_id(self) -> str | None:
        return self._d.get("id")

    def __repr__(self) -> str:
        return f"<Event {self.type} {self._d}>"
