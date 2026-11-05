# 鉴权

## 凭证来源

```ini
# .env（项目根目录，已在 .gitignore 中）
APPID=你的AppID
APPSECRET=你的AppSecret
TIMEOUT=5000      # 可选，HTTP 超时（毫秒），默认 5000
```

也可以直接用环境变量（`QQBOT_APPID` / `QQBOT_APPSECRET` 亦可）。

## 自动换取与注入

调业务接口时**不需要手写任何请求头**：

```python
from qqbotsdk.api.bot import get_me

me = await get_me()
print(me.username)
```

内部流程：

1. 首次请求前用 `APPID`/`APPSECRET` 调 `POST /app/getAppAccessToken` 换 `access_token`；
2. 缓存在进程内，有效期 7200 秒，**剩余不足 60 秒自动刷新**；
3. 并发调用只换取一次（`asyncio.Lock` + 二次检查）；
4. 每个发往 `api.bot.qq.com` 的请求自动附加 `Authorization: QQBot <access_token>`。

## 手动取用

```python
from qqbotsdk.api.auth import get_access_token, get_authorization, reset_access_token

token = await get_access_token()  # 原始 token
await get_authorization()  # "QQBot <token>"
reset_access_token()  # 清缓存（测试或主动失效）
```

## 哪些请求不带鉴权头

- 换取凭证的接口本身（`/app/getAppAccessToken`）；
- 发往其它域名的绝对地址，例如素材上传的 COS 预签名 URL。

## 收尾

```python
from qqbotsdk.api.core import session

await session.close()  # 进程退出前调用，避免 aiohttp 提示会话未关闭
```

`session` 是懒加载单例：可以在任何位置 import，不需要先有事件循环。

## 替换会话（单测）

`session` 只是转发代理，真正的会话由 `get_session()` / `set_session()` 决定。测试里整体换掉它，所有业务模块与 `ctx.api` 都会跟着走假服务端，不会误连真实域名：

```python
from qqbotsdk.api import core

async with core.use_session(local_session):
    ...  # 块内所有请求都打到本地假服务端
```

需要改内部状态（如底层 `ClientSession`）时用 `core.get_session()` 拿真实对象；直接给 `core.session.xxx` 赋值只会写到代理上。

## 常见问题

| 现象 | 原因 |
|---|---|
| `QQBotAuthError: 缺少 APPID / APPSECRET` | `.env` 没读到或变量名不对 |
| `QQBotAuthError: ... code=100016 message='invalid appid or secret'` | AppID/AppSecret 不匹配或已失效 |
| 请求返回 401 | token 过期或被重置，调用 `reset_access_token()` 后重试 |
