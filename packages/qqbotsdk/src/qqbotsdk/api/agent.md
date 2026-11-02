# agent.md — qqbotsdk/api（顶层接口映射）

适用范围：`packages/qqbotsdk/src/qqbotsdk/api/*.py`（`bot.py`、`interaction.py`、`media.py`、`menu.py`、`panel.py`、`user.py`）。
群聊接口见 `group/agent.md`。

凭证获取不在这里：统一用 `qqbotsdk.api.auth.get_access_token()`（`api/app.py` 的重复实现已删除）。

## MUST（必须做）

- MUST 用固定骨架写每个接口（路径参数在前、`payload` 在后、无响应体返回 `None`）：

```python
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
```

- MUST 让查询参数走 `params=payload.model_dump(exclude_none=True)`，请求体走 `json=payload.model_dump(exclude_none=True)`。
- MUST 即使返回 `None` 也要 `await resp.json()`（或 `resp.read()`），确保连接被释放。
- MUST 用 `from qqbotsdk.api.core import session` 拿会话；鉴权、超时、base_url 都由它负责。
- MUST 让函数名与模型名一一对应：`get_panels` ↔ `GetPanelsRequest/GetPanelsResponse`。

## SHOULD（应当做）

- SHOULD 一个文件一个业务域，按官方文档分组；新增域时新建文件，而不是堆进已有文件。
- SHOULD 让 HTTP 方法贴合文档（`PUT` 用于整体替换、`PATCH` 用于局部更新），不要凭习惯改。

## MUST NOT（禁止做）

- MUST NOT 手写 `Authorization` 等鉴权头，也不要自建 `aiohttp.ClientSession`。
- MUST NOT 在接口函数里 `try/except` 吞异常、做重试、做 `sleep`、打印日志——错误让调用方处理。
- MUST NOT 做多接口编排（上传→发送→撤回这类流程由调用方组合）。
- MUST NOT 把路径参数塞进请求模型（如 `group_openid` 不进 `SendGroupMessagesRequest`）。

## 允许的例外

- `media.py`：素材上传需要在本地做格式/大小校验、MD5/SHA1 摘要与直传 COS，属既定例外；改动时保持「校验前移到 prepare、三步拆分（prepare/send/complete）」的结构。
- `media.send_media_image()` 走预签名绝对 URL，**不应**带鉴权头（`api/core.py` 已按域名过滤，别绕过它直接建会话）。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\api
.venv\Scripts\pyright.exe
```
