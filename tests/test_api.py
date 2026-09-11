from qqbotsdk.api import BotApi


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
