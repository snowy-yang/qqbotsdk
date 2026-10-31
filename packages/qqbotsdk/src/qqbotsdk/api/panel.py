from qqbotsdk.api.core import session
from qqbotsdk.model.panel import (
    CreatePanelRequest,
    CreatePanelResponse,
    GetPanelResponse,
    GetPanelsRequest,
    GetPanelsResponse,
    UpdatePanelRequest,
    UpdatePanelResponse,
    UpdatePanelTargetRequest,
)


async def get_panels(
    payload: GetPanelsRequest,
) -> GetPanelsResponse:
    async with session.get(
        "/v2/panels",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetPanelsResponse.model_validate(result)


async def create_panel(
    payload: CreatePanelRequest,
) -> CreatePanelResponse:
    async with session.post(
        "/v2/panels",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreatePanelResponse.model_validate(result)


async def get_panel(
    panel_id: str,
) -> GetPanelResponse:
    async with session.get(
        f"/v2/panels/{panel_id}",
    ) as resp:
        result = await resp.json()

    return GetPanelResponse.model_validate(result)


async def update_panel(
    panel_id: str,
    payload: UpdatePanelRequest,
) -> UpdatePanelResponse:
    async with session.put(
        f"/v2/panels/{panel_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdatePanelResponse.model_validate(result)


async def delete_panel(
    panel_id: str,
) -> None:
    async with session.delete(
        f"/v2/panels/{panel_id}",
    ) as resp:
        await resp.json()


async def update_panel_target(
    panel_id: str,
    payload: UpdatePanelTargetRequest,
) -> None:
    async with session.put(
        f"/v2/panels/{panel_id}/target",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
