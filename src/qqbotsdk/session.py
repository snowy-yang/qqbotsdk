"""WebSocket 会话状态：session_id 与单调递增的 s 序列号。"""


class Session:
    """RESUME 续传所需的状态载体，由 run_loop 构造并在 emitter.services 共享。"""

    def __init__(self) -> None:
        self.session_id: str | None = None
        self._sequence_id: int | None = None

    @property
    def sequence_id(self) -> int | None:
        return self._sequence_id

    def update_sequence(self, value: int) -> None:
        """只接受不回退的序列号，乱序/重放的旧值会被忽略。"""
        current = self._sequence_id or 0
        if value >= current:
            self._sequence_id = value

    @property
    def seq(self) -> int:
        """RESUME 时使用的序列号，无历史序列号时为 0。"""
        return self._sequence_id or 0
