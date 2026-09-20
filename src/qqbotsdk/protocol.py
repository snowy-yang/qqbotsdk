"""协议帧处理器接口：由连接适配器逐帧调用，不走事件队列。

只有业务事件（op=0）进入事件队列交给 `EventEmitter` 分发给用户 handler；
HELLO/READY/INVALID_SESSION/op=13 这类协议帧在适配器内就地处理，因为它们是
握手续传语义——混进业务分发既让用户 handler 看到不该看的协议帧，也让"断线
前重置会话"这类时序取决于分发泵的进度。各接入方式的实现见 `ws_protocol.py`
与 `webhook_protocol.py`。
"""

from abc import ABC, abstractmethod
from typing import Any

from .model import Payload


class BaseProtocol(ABC):
    """适配器专有的协议处理器：实现方返回需要回送的响应体。"""

    @abstractmethod
    async def on_frame(self, payload: Payload) -> Payload | dict[str, Any] | None:
        """处理一条帧，返回需回送的响应体（无需回送则 None）。

        IDENTIFY/RESUME 等握手应答、op=13 验证应答都经返回值回送；业务事件
        （op=0）不必处理，连接器会照常入队分发。
        """
