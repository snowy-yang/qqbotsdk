"""WebSocket 会话状态：session_id 与单调递增的 s 序列号。"""


class Session:
    """RESUME 续传所需的状态载体，由 run_loop 构造并在 emitter.services 共享。"""

    def __init__(self) -> None:
        self.session_id: str | None = None
        self._seq: int | None = None

    @property
    def seq(self) -> int:
        """已收到的最大 s 序列号（心跳/RESUME 用），无历史时为 0。"""
        return self._seq or 0

    def update_sequence(self, value: int) -> None:
        """只接受不回退的序列号，乱序/重放的旧值会被忽略。"""
        if value >= self.seq:
            self._seq = value
