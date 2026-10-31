from qqbotsdk.api.core import session
from qqbotsdk.model.menu import (
    GetMenuResponse,
    UpdateMenuRequest,
    UpdateMenuResponse,
)


async def get_menu() -> GetMenuResponse:
    async with session.get(
        "/v2/menu",
    ) as resp:
        result = await resp.json()

    return GetMenuResponse.model_validate(result)


async def update_menu(
    payload: UpdateMenuRequest,
) -> UpdateMenuResponse:
    async with session.put(
        "/v2/menu",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateMenuResponse.model_validate(result)
