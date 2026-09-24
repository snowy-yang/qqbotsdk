import pytest

from qqbotsdk.config import Config
from qqbotsdk.ws_protocol import get_intents


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("APPID", "123")
    monkeypatch.setenv("APPSECRET", "s")
    monkeypatch.delenv("CONNECTER", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)


def write(tmp_path, content: str) -> str:
    path = tmp_path / "intents.toml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_missing_file_returns_zero(tmp_path):
    assert get_intents(str(tmp_path / "nope.toml")) == 0


def test_enabled_group_sets_bit(tmp_path):
    path = write(tmp_path, "GROUP_AND_C2C_EVENT = true\n")
    assert get_intents(path) & (1 << 25)


def test_only_enabled_groups_are_subscribed(tmp_path):
    path = write(tmp_path, "GUILDS = true\nINTERACTION = false\nAUDIO_ACTION = true\n")
    assert get_intents(path) == (1 << 0) | (1 << 29)


def test_all_disabled_returns_zero(tmp_path):
    path = write(tmp_path, "GUILDS = false\nFORUMS_EVENT = false\n")
    assert get_intents(path) == 0


def test_unknown_group_raises(tmp_path):
    path = write(tmp_path, "NOT_A_GROUP = true\n")
    with pytest.raises(ValueError, match="NOT_A_GROUP"):
        get_intents(path)


def test_non_bool_value_raises(tmp_path):
    path = write(tmp_path, 'GUILDS = "yes"\n')
    with pytest.raises(ValueError, match="true/false"):
        get_intents(path)


def test_legacy_per_event_switches_are_rejected(tmp_path):
    path = write(tmp_path, "[GROUP_AND_C2C_EVENT]\nC2C_MESSAGE_CREATE = true\n")
    with pytest.raises(ValueError, match="true/false"):
        get_intents(path)


def test_config_load_defaults():
    config = Config.load()
    assert config.app_id == "123"
    assert config.app_secret == "s"
    assert config.connecter == "websocket"
    assert config.base_url == "https://api.bot.qq.com"
    assert config.webhook_port == 8080


def test_config_requires_appid(monkeypatch):
    monkeypatch.delenv("APPID", raising=False)
    with pytest.raises(ValueError, match="APPID"):
        Config.load()


def test_config_rejects_unknown_connecter(monkeypatch):
    monkeypatch.setenv("CONNECTER", "carrier-pigeon")
    with pytest.raises(ValueError, match="carrier-pigeon"):
        Config.load()
