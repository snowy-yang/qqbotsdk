from qqbotsdk.api.core import session
from qqbotsdk.model.bot import (
    GenerateUrlLinkRequest,
    GenerateUrlLinkResponse,
    GetGatewayResponse,
    GetMeResponse,
)


async def get_gateway() -> GetGatewayResponse:
    async with session.get(
        "/gateway",
    ) as resp:
        result = await resp.json()

    return GetGatewayResponse.model_validate(result)


async def get_me() -> GetMeResponse:
    async with session.get(
        "/users/@me",
    ) as resp:
        result = await resp.json()

    return GetMeResponse.model_validate(result)


async def generate_url_link(
    payload: GenerateUrlLinkRequest,
) -> GenerateUrlLinkResponse:
    async with session.post(
        "/v2/generate_url_link",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GenerateUrlLinkResponse.model_validate(result)
