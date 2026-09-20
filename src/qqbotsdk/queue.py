"""事件/应答队列：连接层与分发层之间唯一的跨任务通道。"""

from asyncio import Queue

from .model import Payload


class EventQueue:
    """连接层与分发层之间的事件/应答通道。"""

    def __init__(self) -> None:
        self.msg_queue: Queue[Payload] = Queue()
        self.reply_queue: Queue[Payload] = Queue()

    async def put_event(self, item: Payload) -> None:
        await self.msg_queue.put(item)

    async def get_event(self) -> Payload:
        return await self.msg_queue.get()

    async def put_reply(self, item: Payload) -> None:
        await self.reply_queue.put(item)

    async def get_reply(self) -> Payload:
        return await self.reply_queue.get()
