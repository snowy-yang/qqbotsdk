"""事件队列：连接层 → 分发层的单向跨任务通道。

只承载业务事件（op=0）。协议帧由连接适配器就地处理，出站帧（ws 心跳与
协议应答）由适配器自己缓冲，都不经过这里。
"""

from asyncio import Queue

from .model import Payload


class EventQueue:
    """连接层投递、分发层消费的业务事件通道。"""

    def __init__(self) -> None:
        self.msg_queue: Queue[Payload] = Queue()

    async def put_event(self, item: Payload) -> None:
        await self.msg_queue.put(item)

    async def get_event(self) -> Payload:
        return await self.msg_queue.get()
