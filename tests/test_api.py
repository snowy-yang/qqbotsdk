import pytest
from aiohttp import ClientSession, ClientTimeout, web
from aiohttp.test_utils import TestServer

from qqbotsdk.api import ApiError, BotApi, button, keyboard
from qqbotsdk.config import Config
from qqbotsdk.token import AccessToken


def make_api() -> tuple[BotApi, dict]:
    """替换掉 request 记录入参，只测业务方法拼参。"""
    captured: dict = {}

    class Recording(BotApi):
        async def request(self, method, path, **kwargs):  # type: ignore[override]
            captured["call"] = (method, path, kwargs)
            return {}

    return Recording.__new__(Recording), captured


async def test_post_group_message_passive():
    api, cap = make_api()
    await api.post_group_message("G1", content="hi", msg_id="m1", msg_seq=2)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/messages")
    assert kwargs["json"] == {
        "msg_type": 0,
        "content": "hi",
        "msg_id": "m1",
        "msg_seq": 2,
    }


async def test_post_c2c_message_active_no_msg_seq():
    api, cap = make_api()
    await api.post_c2c_message("U1", content="yo")
    _, path, kwargs = cap["call"]
    assert path == "/v2/users/U1/messages"
    assert kwargs["json"] == {"msg_type": 0, "content": "yo"}


async def test_post_message_with_media_sets_msg_type():
    api, cap = make_api()
    media = {"file_info": "f1"}
    await api.post_group_message("G1", content="看图", msg_id="m1", media=media)
    body = cap["call"][2]["json"]
    assert body["msg_type"] == 7
    assert body["media"] == media


async def test_upload_group_file():
    api, cap = make_api()
    await api.upload_group_file("G1", file_type=1, url="http://x/img.png")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/files")
    assert kwargs["json"] == {
        "file_type": 1,
        "url": "http://x/img.png",
        "srv_send_msg": False,
    }


async def test_channel_message_and_reaction():
    api, cap = make_api()
    await api.post_channel_message("C1", content="hi", msg_id="m1", image="http://i")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/channels/C1/messages")
    assert kwargs["json"] == {
        "msg_seq": 1,
        "content": "hi",
        "msg_id": "m1",
        "image": "http://i",
    }

    await api.put_channel_reaction("C1", "m1", emoji_type=1, emoji_id="4")
    assert cap["call"][:2] == ("PUT", "/channels/C1/messages/m1/reactions/1/4")

    await api.delete_channel_reaction("C1", "m1", emoji_type=1, emoji_id="4")
    assert cap["call"][:2] == ("DELETE", "/channels/C1/messages/m1/reactions/1/4")

    await api.withdraw_channel_message("C1", "m1", hide_tip=True)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("DELETE", "/channels/C1/messages/m1")
    assert kwargs["params"] == {"hidetip": "true"}


async def test_withdraw_v2_messages():
    api, cap = make_api()
    await api.withdraw_group_message("G1", "ROBOT1.0_x")
    assert cap["call"][:2] == ("DELETE", "/v2/groups/G1/messages/ROBOT1.0_x")
    await api.withdraw_c2c_message("U1", "ROBOT1.0_y")
    assert cap["call"][:2] == ("DELETE", "/v2/users/U1/messages/ROBOT1.0_y")


async def test_event_id_passive_reply():
    api, cap = make_api()
    await api.post_group_message("G1", content="hi", event_id="e1")
    body = cap["call"][2]["json"]
    assert body["event_id"] == "e1"
    assert "msg_id" not in body
    assert body["msg_seq"] == 1


async def test_mute_and_schedule_official_field_names():
    api, cap = make_api()
    await api.mute_guild_member("GID", "UID", mute_seconds=3600)
    assert cap["call"][2]["json"] == {"mute_seconds": "3600"}

    await api.create_channel_schedule(
        "C1", "活动", "1642076453000", "1642083653000", "C2"
    )
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/channels/C1/schedules")
    info = kwargs["json"]["schedule"]
    assert info["remind_type"] == "0"
    assert "schedule_info" not in kwargs["json"]

    await api.mute_group_member("G1", "2026-01-01T12:00:00+08:00")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/restrict_chat_setting")
    assert kwargs["json"] == {"mute_expire_at": "2026-01-01T12:00:00+08:00"}


async def test_me():
    api, cap = make_api()
    await api.me()
    assert cap["call"][:2] == ("GET", "/users/@me")


async def test_post_message_markdown_and_keyboard():
    api, cap = make_api()
    kb = {"content": {"rows": []}}
    await api.post_group_message("G1", markdown="# 标题", keyboard=kb, msg_id="m1")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/messages")
    body = kwargs["json"]
    assert body["msg_type"] == 2
    assert body["markdown"] == {"content": "# 标题"}
    assert "content" not in body  # markdown 与 content 互斥
    assert body["keyboard"] == kb
    assert body["msg_id"] == "m1"


async def test_post_message_markdown_dict_and_event_id():
    api, cap = make_api()
    await api.post_c2c_message(
        "U1", markdown={"content": "# t"}, event_id="e1", msg_seq=2
    )
    body = cap["call"][2]["json"]
    assert body["msg_type"] == 2
    assert body["markdown"] == {"content": "# t"}
    assert body["event_id"] == "e1"
    assert body["msg_seq"] == 2


async def test_media_takes_precedence_over_markdown():
    api, cap = make_api()
    await api.post_group_message(
        "G1", content="看图", msg_id="m1", media={"file_info": "f"}, markdown="# t"
    )
    body = cap["call"][2]["json"]
    assert body["msg_type"] == 7
    assert "markdown" not in body


async def test_respond_interaction():
    api, cap = make_api()
    await api.respond_interaction("I1")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/interactions/I1")
    assert kwargs["json"] == {"code": 0}


def test_button_defaults_and_overrides():
    btn = button("点我", data="d1")
    assert btn["render_data"] == {"label": "点我", "style": 1}
    assert btn["action"] == {"type": 1, "permission": {"type": 2}, "data": "d1"}
    assert len(btn["id"]) == 8  # 未指定 id 时自动生成短 id

    btn2 = button("跳转", data="https://x", type=0, permission=1, style=0, id="b2")
    assert btn2["id"] == "b2"
    assert btn2["action"]["type"] == 0
    assert btn2["action"]["permission"] == {"type": 1}
    assert btn2["render_data"]["style"] == 0


def test_keyboard_rows():
    b1, b2, b3 = button("a", data="1"), button("b", data="2"), button("c", data="3")
    kb = keyboard(b1, [b2, b3])
    rows = kb["content"]["rows"]
    assert rows[0]["buttons"] == [b1]  # 单按钮独占一行
    assert rows[1]["buttons"] == [b2, b3]  # 列表同行并排
    assert len(rows) == 2


async def test_request_tolerates_non_json_content_type():
    """回应互动等接口 200 响应的 Content-Type 是 text/plain（body 为 JSON），
    request 不应抛 ContentTypeError（真实 HTTP 栈回归）。"""

    async def handler(request):
        return web.Response(text="{}", content_type="text/plain")

    app = web.Application()
    app.router.add_route("PUT", "/interactions/I1", handler)
    server = TestServer(app)
    await server.start_server()
    try:
        config = Config(
            app_id="id",
            app_secret="s",
            base_url=f"http://{server.host}:{server.port}",
            timeout=ClientTimeout(total=5),
            connecter="websocket",
            intents_file="intents.toml",
            webhook_host="0.0.0.0",
            webhook_port=8080,
            webhook_path="/qqbot/webhook",
        )

        class FixedToken(AccessToken):
            async def get_access_token(self) -> str:
                return "test-token"

        http = ClientSession()
        try:
            api = BotApi(config, http, FixedToken(config, http))
            assert await api.respond_interaction("I1") == {}
        finally:
            await http.close()
    finally:
        await server.close()


# ---------- 请求内核：429 限流重试 / 401 刷新 token 重试 ----------


class ScriptedResponse:
    def __init__(self, status: int, payload, headers: dict | None = None) -> None:
        self.status = status
        self.headers = headers or {}
        self._payload = payload

    async def json(self, **kwargs):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class ScriptedSession:
    """按序弹出响应，记录 request 调用。"""

    def __init__(self, *responses: ScriptedResponse) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs):
        self.calls.append((method, url))
        return self._responses.pop(0)


class StubToken:
    def __init__(self) -> None:
        self.fetches = 0
        self.invalidated = 0

    async def get_access_token(self) -> str:
        self.fetches += 1
        return "t1"

    def invalidate(self) -> None:
        self.invalidated += 1


def make_core_api(http: ScriptedSession, token: StubToken | None = None) -> BotApi:
    config = Config(
        app_id="id",
        app_secret="s",
        base_url="https://x",
        timeout=ClientTimeout(total=5),
        connecter="websocket",
        intents_file="intents.toml",
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/qqbot/webhook",
    )
    return BotApi(config, http, token or StubToken())  # type: ignore[arg-type]


async def test_request_retries_429_honoring_retry_after(monkeypatch):
    delays: list[float] = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("qqbotsdk.api.core.asyncio.sleep", fake_sleep)
    http = ScriptedSession(
        ScriptedResponse(
            429, {"code": 11244, "message": "limit"}, {"Retry-After": "2"}
        ),
        ScriptedResponse(200, {"ok": 1}),
    )
    api = make_core_api(http)
    assert await api.request("POST", "/v1/x") == {"ok": 1}
    assert len(http.calls) == 2
    assert delays == [2.0]


async def test_request_429_dirty_header_falls_back_to_backoff(monkeypatch):
    delays: list[float] = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("qqbotsdk.api.core.asyncio.sleep", fake_sleep)
    http = ScriptedSession(
        # 线上见过的脏值 "30,120"：取首段 30
        ScriptedResponse(429, {}, {"Retry-After": "30,120"}),
        # 无 Retry-After：指数退避 1 * 2**1 = 2
        ScriptedResponse(429, {}),
        ScriptedResponse(200, {}),
    )
    api = make_core_api(http)
    assert await api.get("/v1/x") == {}
    assert delays == [30.0, 2.0]


async def test_request_429_retry_after_capped(monkeypatch):
    delays: list[float] = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("qqbotsdk.api.core.asyncio.sleep", fake_sleep)
    http = ScriptedSession(
        ScriptedResponse(429, {}, {"Retry-After": "3600"}),
        ScriptedResponse(200, {}),
    )
    api = make_core_api(http)
    await api.get("/v1/x")
    assert delays == [30.0]  # 封顶，不真睡一小时


async def test_request_429_exhausted_raises_api_error(monkeypatch):
    async def fake_sleep(delay):
        pass

    monkeypatch.setattr("qqbotsdk.api.core.asyncio.sleep", fake_sleep)
    http = ScriptedSession(*(ScriptedResponse(429, {}) for _ in range(4)))
    api = make_core_api(http)
    with pytest.raises(ApiError) as exc_info:
        await api.get("/v1/x")
    assert exc_info.value.status == 429
    assert len(http.calls) == 4  # 首次 + 3 次重试


async def test_request_401_invalidates_token_and_retries_once():
    http = ScriptedSession(
        ScriptedResponse(401, {"code": -1, "message": "unauthorized"}),
        ScriptedResponse(200, {"ok": 1}),
    )
    token = StubToken()
    api = make_core_api(http, token)
    assert await api.get("/v1/x") == {"ok": 1}
    assert token.invalidated == 1
    assert token.fetches == 2
    assert len(http.calls) == 2
