from qqbotsdk.api.core import session
from qqbotsdk.model.app import (
    GetAppAccessTokenRequest,
    GetAppAccessTokenResponse,
)


async def get_app_access_token(
    payload: GetAppAccessTokenRequest,
) -> GetAppAccessTokenResponse:
    async with session.post(
        "/app/getAppAccessToken",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetAppAccessTokenResponse.model_validate(result)
