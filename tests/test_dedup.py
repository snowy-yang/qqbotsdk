from qqbotsdk.config import Config
from qqbotsdk.connecter import WebhookConnecter
from qqbotsdk.queue import EventQueue


def make_connecter() -> WebhookConnecter:
    config = Config(
        app_id="app",
        app_secret="secret",
        base_url="https://api.bot.qq.com",
        timeout=None,  # type: ignore[arg-type]
        connecter="webhook",
        intents_file="intents.toml",
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/qqbot/webhook",
    )

    async def noop_handle(payload):
        return None

    return WebhookConnecter(config, EventQueue(), noop_handle)


def test_first_push_is_not_duplicate():
    c = make_connecter()
    assert not c._duplicated("evt-1")


def test_same_id_within_ttl_is_duplicate():
    c = make_connecter()
    assert not c._duplicated("evt-1")
    assert c._duplicated("evt-1")


def test_none_or_empty_id_never_duplicates():
    c = make_connecter()
    assert not c._duplicated(None)
    assert not c._duplicated("")
    assert not c._duplicated(None)


def test_expired_entries_are_evicted():
    c = make_connecter()
    assert not c._duplicated("evt-1")
    # 人为把记录改成过期
    for key in list(c._seen):
        c._seen[key] -= c._DEDUP_TTL + 1
    assert not c._duplicated("evt-1")
    assert "evt-1" in c._seen  # 以新时间戳重新记录
