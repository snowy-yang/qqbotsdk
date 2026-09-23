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


async def test_panel_create_list_detail():
    api, cap = make_api()
    panel = {"items": [{"type": "command", "name": "群签到", "desc": "每日签到"}]}
    await api.create_panel(
        "group", panel, target_type="specific", group_openids=["G1", "G2"]
    )
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/panels")
    assert kwargs["json"] == {
        "scope": "group",
        "panel": panel,
        "target_type": "specific",
        "group_openids": ["G1", "G2"],
    }

    await api.get_panels("c2c", cursor="c1", limit=10)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/v2/panels")
    assert kwargs["params"] == {"scope": "c2c", "cursor": "c1", "limit": 10}

    await api.get_panel("P1")
    assert cap["call"][:2] == ("GET", "/v2/panels/P1")


async def test_panel_update_delete_targets():
    api, cap = make_api()
    panel = {"items": [{"type": "command", "name": "新指令", "desc": "更新"}]}
    await api.update_panel("P1", panel)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/v2/panels/P1")
    assert kwargs["json"] == {"panel": panel}

    await api.delete_panel("P1")
    assert cap["call"][:2] == ("DELETE", "/v2/panels/P1")

    await api.update_panel_targets("P1", "add", group_openids=["G3"])
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/v2/panels/P1/target")
    assert kwargs["json"] == {"op": "add", "group_openids": ["G3"]}

    await api.update_panel_targets("P1", "del", user_openids=["U1"])
    assert cap["call"][2]["json"] == {"op": "del", "user_openids": ["U1"]}


async def test_menu_get_and_update():
    api, cap = make_api()
    await api.get_menu()
    assert cap["call"][:2] == ("GET", "/v2/menu")

    menu = {
        "items": [
            {"type": "send_message", "name": "帮助", "send_message": "/help"},
            {"type": "link", "name": "官网", "link": "https://example.com"},
        ]
    }
    await api.update_menu(menu)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/v2/menu")
    assert kwargs["json"] == {"menu": menu}


# ---------- v2 补充：流式消息 / 分片上传 / 分享链接 ----------


async def test_stream_message_first_and_next_chunk():
    api, cap = make_api()
    await api.post_c2c_stream_message("U1", "回答中", msg_id="m1", msg_seq=1)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/users/U1/stream_messages")
    assert kwargs["json"] == {
        "index": 0,
        "input_state": 1,
        "content_type": "markdown",
        "content_raw": "回答中",
        "msg_id": "m1",
        "msg_seq": 1,
    }

    await api.post_c2c_stream_message(
        "U1",
        "回答中，更多内容",
        stream_msg_id="s1",
        index=1,
        input_state=10,
        input_mode="replace",
        event_id="e1",
    )
    body = cap["call"][2]["json"]
    assert body["stream_msg_id"] == "s1"
    assert body["index"] == 1
    assert body["input_state"] == 10
    assert body["input_mode"] == "replace"
    assert body["event_id"] == "e1"
    assert "msg_id" not in body


async def test_chunked_upload_group_and_c2c():
    api, cap = make_api()
    common = {
        "file_type": 2,
        "file_size": 31457280,
        "file_name": "demo.mp4",
        "md5": "m",
        "sha1": "s",
        "md5_10m": "m10",
    }
    await api.prepare_group_upload("G1", **common)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/upload_prepare")
    assert kwargs["json"] == {
        "file_type": 2,
        "file_size": "31457280",  # 官方为字符串类型
        "file_name": "demo.mp4",
        "md5": "m",
        "sha1": "s",
        "md5_10m": "m10",
    }

    await api.finish_group_upload_part("G1", "up1", part_index=0)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/upload_part_finish")
    assert kwargs["json"] == {"upload_id": "up1", "part_index": 0}

    await api.prepare_c2c_upload("U1", **common)
    assert cap["call"][:2] == ("POST", "/v2/users/U1/upload_prepare")

    await api.finish_c2c_upload_part("U1", "up1", part_index=1, block_size=4096, md5="p1")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/users/U1/upload_part_finish")
    assert kwargs["json"] == {
        "upload_id": "up1",
        "part_index": 1,
        "block_size": "4096",
        "md5": "p1",
    }


async def test_generate_url_link():
    api, cap = make_api()
    await api.generate_url_link()
    assert cap["call"][2]["json"] == {}

    await api.generate_url_link("track_01")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/generate_url_link")
    assert kwargs["json"] == {"callback_data": "track_01"}


# ---------- 频道补充：子频道增删改 / 机器人频道列表 ----------


async def test_channel_manage_and_me_guilds():
    api, cap = make_api()
    await api.create_channel("GID", "公告区", type=0, sub_type=1, position=3)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/guilds/GID/channels")
    assert kwargs["json"] == {"name": "公告区", "type": 0, "sub_type": 1, "position": 3}

    await api.update_channel("C1", name="新名字", position=5)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PATCH", "/channels/C1")
    assert kwargs["json"] == {"name": "新名字", "position": 5}

    await api.delete_channel("C1")
    assert cap["call"][:2] == ("DELETE", "/channels/C1")

    await api.get_me_guilds(after="G9", limit=20)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/users/@me/guilds")
    assert kwargs["params"] == {"after": "G9", "limit": 20}

    await api.get_me_guilds()
    assert cap["call"][2].get("params") is None


# ---------- 群管理 ----------


async def test_group_info_members_state():
    api, cap = make_api()
    await api.get_group_info("G1")
    assert cap["call"][:2] == ("GET", "/v2/groups/G1/info")

    await api.get_group_members("G1", cursor="c1")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/v2/groups/G1/members")
    assert kwargs["params"] == {"cursor": "c1"}

    await api.get_group_member("G1", "M1")
    assert cap["call"][:2] == ("GET", "/v2/groups/G1/members/M1")

    await api.get_group_bot_state("G1")
    assert cap["call"][:2] == ("GET", "/v2/groups/G1/bot_state")

    await api.get_group_mute_state("G1")
    assert cap["call"][:2] == ("GET", "/v2/groups/G1/restrict_chat_setting")


async def test_group_join_request_flow():
    api, cap = make_api()
    await api.get_group_join_requests("G1", limit=10)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/v2/groups/G1/join_request_list")
    assert kwargs["params"] == {"limit": 10}

    await api.review_group_join_request(
        "G1", "M1", "approve", join_request_id="j1"
    )
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/approval_join_request/M1")
    assert kwargs["json"] == {"op": "approve", "join_request_id": "j1"}

    await api.review_group_join_request(
        "G1", "M1", "decline", join_request_id="j1",
        reject_reason="广告", add_to_member_blacklist=True,
    )
    body = cap["call"][2]["json"]
    assert body == {
        "op": "decline",
        "join_request_id": "j1",
        "reject_reason": "广告",
        "add_to_member_blacklist": True,
    }


async def test_group_blacklist_and_remove():
    api, cap = make_api()
    await api.get_group_blacklist("G1", cursor="c1", limit=50)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/v2/groups/G1/member_blacklist")
    assert kwargs["params"] == {"cursor": "c1", "limit": 50}

    await api.update_group_blacklist("G1", "add", ["M1", "M2"])
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/member_blacklist")
    assert kwargs["json"] == {"op": "add", "member_openids": ["M1", "M2"]}

    await api.remove_group_members("G1", ["M1"], add_to_member_blacklist=True)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/G1/batch_remove_members")
    assert kwargs["json"] == {
        "member_openids": ["M1"],
        "add_to_member_blacklist": True,
    }


async def test_join_approval_strategies():
    api, cap = make_api()
    await api.get_join_approval_strategies(cursor="c1", limit=20)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("GET", "/v2/groups/join_approval_strategy")
    assert kwargs["params"] == {"cursor": "c1", "limit": 20}

    await api.create_join_approval_strategy(
        group_openids=["G1"], expire_at="2027-08-05T15:30:16+08:00"
    )
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/v2/groups/join_approval_strategy")
    assert kwargs["json"] == {
        "group_openids": ["G1"],
        "expire_at": "2027-08-05T15:30:16+08:00",
    }

    await api.update_join_approval_strategy(
        "st1", is_enable="off", group_action={"op": "add", "group_openids": ["G2"]}
    )
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PATCH", "/v2/groups/join_approval_strategy/st1")
    assert kwargs["json"] == {
        "is_enable": "off",
        "group_action": {"op": "add", "group_openids": ["G2"]},
    }

    await api.delete_join_approval_strategy("st1")
    assert cap["call"][:2] == ("DELETE", "/v2/groups/join_approval_strategy/st1")

    await api.execute_join_approval_strategy("st1")
    assert cap["call"][:2] == ("POST", "/v2/groups/join_approval_strategy/st1/execute")

    await api.update_join_approval_strategy_whitelist("st1", "add", ["1234567"])
    method, path, kwargs = cap["call"]
    assert (method, path) == (
        "POST",
        "/v2/groups/join_approval_strategy/st1/whitelist_users",
    )
    assert kwargs["json"] == {"op": "add", "whitelist_users": ["1234567"]}


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


# ---------- 旧版（频道侧）接口补齐 ----------


async def test_guild_roles_crud_and_member_role():
    api, cap = make_api()
    await api.create_guild_role("GID", "码农", color=0xFF0000, hoist=1)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/guilds/GID/roles")
    assert kwargs["json"] == {"name": "码农", "color": 16711680, "hoist": 1}

    await api.update_guild_role("GID", "R1", name="新名")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PATCH", "/guilds/GID/roles/R1")
    assert kwargs["json"] == {"name": "新名"}

    await api.delete_guild_role("GID", "R1")
    assert cap["call"][:2] == ("DELETE", "/guilds/GID/roles/R1")

    await api.add_guild_member_role("GID", "U1", "R1")
    assert cap["call"][:2] == ("PUT", "/guilds/GID/members/U1/roles/R1")

    await api.remove_guild_member_role("GID", "U1", "R1")
    assert cap["call"][:2] == ("DELETE", "/guilds/GID/members/U1/roles/R1")


async def test_guild_members_mutes_and_api_permission():
    api, cap = make_api()
    await api.get_guild_members("GID")
    assert cap["call"][:2] == ("GET", "/guilds/GID/members")

    await api.remove_guild_member("GID", "U1", add_blacklist=True, delete_history_msg_days=7)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("DELETE", "/guilds/GID/members/U1")
    assert kwargs["json"] == {"add_blacklist": True, "delete_history_msg_days": 7}

    await api.get_role_members("GID", "R1")
    assert cap["call"][:2] == ("GET", "/guilds/GID/roles/R1/members")

    await api.get_channel_online_nums("C1")
    assert cap["call"][:2] == ("GET", "/channels/C1/online_nums")

    await api.mute_guild("GID", mute_seconds="60")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PATCH", "/guilds/GID/mute")
    assert kwargs["json"] == {"mute_seconds": "60"}

    await api.mute_guild_members("GID", ["U1", "U2"], mute_end_timestamp="1700000000")
    assert cap["call"][2]["json"] == {
        "user_ids": ["U1", "U2"],
        "mute_end_timestamp": "1700000000",
    }

    await api.get_guild_message_setting("GID")
    assert cap["call"][:2] == ("GET", "/guilds/GID/message/setting")

    await api.get_guild_api_permissions("GID")
    assert cap["call"][:2] == ("GET", "/guilds/GID/api_permission")

    await api.create_api_permission_demand("GID", "C1", "/channels/x/messages", "POST", "d")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/guilds/GID/api_permission/demand")
    assert kwargs["json"] == {
        "channel_id": "C1",
        "api_identify": {"path": "/channels/x/messages", "method": "POST"},
        "desc": "d",
    }


async def test_channel_permissions_and_dms():
    api, cap = make_api()
    await api.get_channel_permissions("C1", "U1")
    assert cap["call"][:2] == ("GET", "/channels/C1/members/U1/permissions")

    await api.get_channel_role_permissions("C1", "R1")
    assert cap["call"][:2] == ("GET", "/channels/C1/roles/R1/permissions")

    await api.update_channel_permissions("C1", "U1", add="1", remove="4")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/channels/C1/members/U1/permissions")
    assert kwargs["json"] == {"add": "1", "remove": "4"}

    await api.update_channel_role_permissions("C1", "R1", add="2")
    assert cap["call"][2]["json"] == {"add": "2"}

    await api.create_dms("U1", "GID")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/users/@me/dms")
    assert kwargs["json"] == {"recipient_id": "U1", "source_guild_id": "GID"}

    await api.post_dms_message("DG", content="hi", msg_id="m1", msg_seq=2)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/dms/DG/messages")
    assert kwargs["json"] == {"msg_seq": 2, "content": "hi", "msg_id": "m1"}

    await api.withdraw_dms_message("DG", "m1", hide_tip=True)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("DELETE", "/dms/DG/messages/m1")
    assert kwargs["params"] == {"hidetip": "true"}


async def test_audio_and_forum():
    api, cap = make_api()
    await api.control_channel_audio("C1", audio_url="http://x/a.mp3", text="歌名")
    method, path, kwargs = cap["call"]
    assert (method, path) == ("POST", "/channels/C1/audio")
    assert kwargs["json"] == {
        "status": 0,
        "audio_url": "http://x/a.mp3",
        "text": "歌名",
    }

    await api.control_channel_audio("C1", status=3)
    assert cap["call"][2]["json"] == {"status": 3}

    await api.put_channel_mic("C1")
    assert cap["call"][:2] == ("PUT", "/channels/C1/mic")
    await api.delete_channel_mic("C1")
    assert cap["call"][:2] == ("DELETE", "/channels/C1/mic")

    await api.get_channel_threads("C1")
    assert cap["call"][:2] == ("GET", "/channels/C1/threads")

    await api.get_channel_thread("C1", "T1")
    assert cap["call"][:2] == ("GET", "/channels/C1/threads/T1")

    await api.put_channel_thread("C1", "标题", "内容", format=3)
    method, path, kwargs = cap["call"]
    assert (method, path) == ("PUT", "/channels/C1/threads")
    assert kwargs["json"] == {"title": "标题", "content": "内容", "format": 3}

    await api.delete_channel_thread("C1", "T1")
    assert cap["call"][:2] == ("DELETE", "/channels/C1/threads/T1")
