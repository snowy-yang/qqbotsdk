from qqbotsdk.api.core import session
from qqbotsdk.model.sub.upload import (
    UploadPartFinishRequest,
    UploadPrepareRequest,
)
from qqbotsdk.model.user.messages import (
    PrepareUserUploadResponse,
    SendUserMessagesRequest,
    SendUserMessagesResponse,
    UploadUserFileRequest,
    UploadUserFileResponse,
)
from qqbotsdk.model.user.stream_messages import (
    SendUserStreamMessagesRequest,
    SendUserStreamMessagesResponse,
)


async def send_user_messages(
    user_openid: str,
    payload: SendUserMessagesRequest,
) -> SendUserMessagesResponse:
    async with session.post(
        f"/v2/users/{user_openid}/messages",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return SendUserMessagesResponse.model_validate(result)


async def recall_user_messages(
    user_openid: str,
    message_id: str,
) -> None:
    async with session.delete(
        f"/v2/users/{user_openid}/messages/{message_id}",
    ) as resp:
        await resp.json()


async def upload_user_file(
    user_openid: str,
    payload: UploadUserFileRequest,
) -> UploadUserFileResponse:
    async with session.post(
        f"/v2/users/{user_openid}/files",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UploadUserFileResponse.model_validate(result)


async def prepare_user_upload(
    user_openid: str,
    payload: UploadPrepareRequest,
) -> PrepareUserUploadResponse:
    async with session.post(
        f"/v2/users/{user_openid}/upload_prepare",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return PrepareUserUploadResponse.model_validate(result)


async def finish_user_upload_part(
    user_openid: str,
    payload: UploadPartFinishRequest,
) -> None:
    async with session.post(
        f"/v2/users/{user_openid}/upload_part_finish",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def send_user_stream_messages(
    user_openid: str,
    payload: SendUserStreamMessagesRequest,
) -> SendUserStreamMessagesResponse:
    async with session.post(
        f"/v2/users/{user_openid}/stream_messages",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return SendUserStreamMessagesResponse.model_validate(result)
