import pytest

from qqbotsdk.config import Config
from qqbotsdk.ws_protocol import get_intents, resolve_intents


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


# --- 掩码直传：Config.intents（INTENTS 环境变量 / Bot 参数）优先于 intents.toml ---


def test_config_intents_env_decimal(monkeypatch):
    monkeypatch.setenv("INTENTS", str((1 << 25) | (1 << 26)))
    assert Config.load().intents == (1 << 25) | (1 << 26)


def test_config_intents_env_hex(monkeypatch):
    monkeypatch.setenv("INTENTS", "0x4000000")
    assert Config.load().intents == 1 << 26


def test_config_intents_env_invalid(monkeypatch):
    monkeypatch.setenv("INTENTS", "abc")
    with pytest.raises(ValueError, match="INTENTS"):
        Config.load()


def make_config(intents: int | None, path: str) -> Config:
    return Config(
        app_id="app",
        app_secret="secret",
        base_url="https://api.bot.qq.com",
        timeout=None,  # type: ignore[arg-type]
        connecter="websocket",
        intents_file=path,
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/x",
        intents=intents,
    )


def test_resolve_intents_mask_wins_over_file(tmp_path):
    path = write(tmp_path, "GUILDS = true\n")
    assert resolve_intents(make_config(1 << 26, path)) == 1 << 26


def test_resolve_intents_falls_back_to_file(tmp_path):
    path = write(tmp_path, "GUILDS = true\nAUDIO_ACTION = true\n")
    assert resolve_intents(make_config(None, path)) == (1 << 0) | (1 << 29)


def test_resolve_intents_unknown_bits_pass_through(tmp_path):
    mask = (1 << 26) | (1 << 5)  # 1<<5 未收录进 Intent 枚举
    assert resolve_intents(make_config(mask, str(tmp_path / "nope.toml"))) == mask
