from aiohttp import ClientSession

session = ClientSession(
    base_url="https://api.bot.qq.com",
    raise_for_status=True,
)

__all__ = [
    "session",
]
