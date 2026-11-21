from qqbotsdk.api.core import session
from qqbotsdk.model.sub.upload import (
    UploadPartFinishRequest,
    UploadPrepareRequest,
)
from qqbotsdk.model.user.info import GetUserInfoResponse
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


async def get_user_info(
    user_openid: str,
) -> GetUserInfoResponse:
    """获取用户基本信息.

    官方 2026-11-16 新增, 频率 10 QPS. 与好友无关系时平台返回 ``40184001``.
    响应里的 ``allow_proactive_msg`` 可用于判断能否给该用户下发主动消息.
    """
    async with session.get(
        f"/v2/users/{user_openid}/info",
    ) as resp:
        result = await resp.json()

    return GetUserInfoResponse.model_validate(result)


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
