from qqbotsdk.api.core import session
from qqbotsdk.model.interaction import (
    ConfirmInteractionsRequest,
)


async def confirm_interactions(
    interaction_id: str,
    payload: ConfirmInteractionsRequest,
) -> None:
    async with session.put(
        f"/interactions/{interaction_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
