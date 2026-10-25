"""素材管理方法集（官方 2026-10-21 新增）：Markdown 图片预上传平台，
获得 qqbot-media:// 引用写入 Markdown 消息，无需依赖公网图床；图片在
有效期内可反复引用，发送时由平台自动转存。

限制（官方文档 2026-10 核对）：单张 ≤10MB，仅 png/jpeg/gif/webp（扩展名
须与 Content-Type 一致），单机器人 100 张（删除释放配额），上传任务
（upload_id）4 小时有效，图片自最后一次被消息引用起 90 天滑动过期。
"""

import hashlib
from typing import Any

from .core import ApiError, BaseApi

# content_type 取值（素材管理仅支持这四类图片）
MEDIA_IMAGE_PNG = "image/png"
MEDIA_IMAGE_JPEG = "image/jpeg"
MEDIA_IMAGE_GIF = "image/gif"
MEDIA_IMAGE_WEBP = "image/webp"

# 单张图片大小上限（超限服务端报 40035002，本地提前拦截）
MEDIA_IMAGE_MAX_BYTES = 10 * 1024 * 1024


class MediaApi(BaseApi):
    """素材管理方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    async def prepare_media_image(
        self,
        file_name: str,
        file_size: int,
        content_type: str,
        md5: str,
        sha1: str,
    ) -> dict:
        """申请图片上传（POST /v2/media-images/prepare）。

        返回 {"upload_id", "presigned_url", "expires_in"}：PUT 图片
        二进制到 presigned_url（请求头 Content-Type 必须与此处声明的
        content_type 完全一致，否则 COS 拒绝 403）后调
        complete_media_image。upload_id 4 小时内有效；md5/sha1 为文件
        内容摘要（32/40 位十六进制）；数量超 100 张报 40035007。
        """
        body: dict[str, Any] = {
            "file_name": file_name,
            "file_size": file_size,
            "content_type": content_type,
            "md5": md5,
            "sha1": sha1,
        }
        return await self.post("/v2/media-images/prepare", json=body)

    async def complete_media_image(self, upload_id: str, md5: str) -> dict:
        """完成图片上传（POST /v2/media-images/complete）。

        md5 为直传后 COS 响应的 ETag（去引号即文件 MD5，服务端比对不
        一致报 40035003）。返回 {"image_id", "url", "ttl", "preview_url"}：
        url 即 Markdown 引用链接（![说明 #宽px #高px](url)），ttl 为
        滑动过期窗口秒数（90 天），preview_url 短时效仅供发送前自查，
        不要持久化存储。
        """
        return await self.post(
            "/v2/media-images/complete", json={"upload_id": upload_id, "md5": md5}
        )

    async def upload_media_image(
        self,
        data: bytes,
        file_name: str,
        content_type: str = MEDIA_IMAGE_PNG,
    ) -> dict:
        """一步上传图片素材：prepare → PUT 直传 → complete。

        data 为图片二进制（≤10MB，超限抛 ValueError；md5/sha1 自动
        计算），返回 complete_media_image 的响应，url 直接写入
        Markdown。
        """
        if len(data) > MEDIA_IMAGE_MAX_BYTES:
            raise ValueError(
                f"图片 {len(data)} 字节超过上限 {MEDIA_IMAGE_MAX_BYTES}（10MB）"
            )
        md5 = hashlib.md5(data).hexdigest()
        prepared = await self.prepare_media_image(
            file_name, len(data), content_type, md5, hashlib.sha1(data).hexdigest()
        )
        # 预签名 URL 直传不经请求内核（COS 不收 QQBot 鉴权头）
        async with self._http.put(
            prepared["presigned_url"],
            data=data,
            headers={"Content-Type": content_type},
        ) as resp:
            if resp.status >= 400:
                detail = (await resp.content.read(200)).decode("utf-8", "replace")
                raise ApiError(
                    resp.status,
                    None,
                    "图片直传失败：Content-Type 需与 prepare 声明一致，"
                    f"或预签名 URL 已过期（重新 prepare）；body={detail!r}",
                )
            etag = (resp.headers.get("ETag") or "").strip('"')
            if etag and etag != md5:
                raise ApiError(
                    resp.status, None, f"直传 ETag {etag} 与本地 MD5 {md5} 不一致"
                )
        return await self.complete_media_image(prepared["upload_id"], md5)

    async def get_media_images(self, cursor: str | None = None) -> dict:
        """查询有效图片列表（GET /v2/media-images），按上传时间倒序。

        首页不传 cursor，翻页传上一页返回的 next_cursor（为空表示已到
        末页）；返回 {"images": [...], "next_cursor", "total"}，total
        与 100 张配额同一口径。images[] 含 image_id/url/file_name/
        preview_url/created_at/expires_at。
        """
        params = {"cursor": cursor} if cursor else None
        return await self.get("/v2/media-images", params=params)

    async def delete_media_image(self, image_id: str) -> dict:
        """删除图片素材（DELETE /v2/media-images/{image_id}/delete）。

        释放数量配额；引用链接立即失效，不能再被新消息引用（已发出的
        消息不受影响）；删除不存在的 id 报 40035008。返回空 JSON 对象。
        """
        return await self.delete(f"/v2/media-images/{image_id}/delete")
