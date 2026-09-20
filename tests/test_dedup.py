from time import monotonic

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


def test_expired_id_is_treated_as_new():
    """TTL 之外重发的同一 id 是新事件，不能被当成重复丢掉。"""
    c = make_connecter()
    assert not c._duplicated("evt-x")
    c._seen["evt-x"] -= c._DEDUP_TTL + 1  # 只把这一个改成过期
    assert not c._duplicated("evt-x")


def test_table_is_swept_only_at_threshold():
    """表长未到阈值时不做全表清理（摊还 O(1)），过期项留在表里也不影响判定。"""
    c = make_connecter()
    assert not c._duplicated("old")
    c._seen["old"] -= c._DEDUP_TTL + 1
    assert not c._duplicated("new")  # 未到阈值：不清理
    assert "old" in c._seen
    # 灌到阈值，下一次判定触发清理，过期项被移除
    for i in range(c._DEDUP_SWEEP_AT):
        c._seen[f"filler-{i}"] = monotonic()
    assert not c._duplicated("another")
    assert "old" not in c._seen
