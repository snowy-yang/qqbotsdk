from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class UploadPart(QQBotBaseModel):
    index: int | None = Field(
        default=None,
        description="分片序号，从 0 开始",
    )
    presigned_url: str | None = Field(
        default=None,
        description="预签名上传 URL，客户端通过 HTTP PUT 将分片数据上传到此 URL",
    )
    block_size: str | None = Field(
        default=None,
        description="该分块的大小（字节）",
    )


class UploadConfig(QQBotBaseModel):
    concurrency: int | None = Field(
        default=None,
        description="上传并发数，默认 1",
    )
    retry_timeout: int | None = Field(
        default=None,
        description="重试超时时间（秒），默认 300（5 分钟）",
    )
    retry_delay: int | None = Field(
        default=None,
        description="重试延迟（秒），默认 1",
    )


class UploadPrepareResponse(QQBotBaseModel):
    upload_id: str | None = Field(
        default=None,
        description="上传任务 ID，后续分片上传和完成合并时需携带",
    )
    block_size: str | None = Field(
        default=None,
        description="分块大小（字节），默认 5MB",
    )
    parts: list[UploadPart] | None = Field(
        default=None,
        description="分片列表，每个分片包含一个预签名上传 URL",
    )
    upload_config: UploadConfig | None = Field(
        default=None,
        description="上传配置，控制客户端上传行为",
    )


class UploadPartFinishRequest(QQBotRequestModel):
    upload_id: str | None = Field(
        default=None,
        description="上传任务 ID，来自预上传响应",
    )
    part_index: int | None = Field(
        default=None,
        description="分片序号，对应 UploadPart.index",
    )
    block_size: str | None = Field(
        default=None,
        description="该分块的实际大小（字节）",
    )
    md5: str | None = Field(
        default=None,
        description="该分片的 MD5 校验值",
    )


class UploadPrepareRequest(QQBotRequestModel):
    file_type: Literal[1, 2, 3, 4] = Field(
        ...,
        description="业务类型：1=图片，2=视频，3=语音，4=文件，超过软限制会降级为文件类型",
    )
    file_size: str = Field(
        ...,
        description="文件大小（字节），字符串形式",
    )
    file_name: str = Field(
        ...,
        description="文件名",
    )
    md5: str = Field(
        ...,
        description="整个文件的 MD5 校验值",
    )
    sha1: str = Field(
        ...,
        description="整个文件的 SHA1 校验值",
    )
    md5_10m: str = Field(
        ...,
        description="文件前 10002432 字节（约 10MB）的 MD5 校验值",
    )
