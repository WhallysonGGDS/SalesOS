import pytest
from pydantic import SecretStr, ValidationError

from salesos.config import Settings


def test_defaults_are_local_only() -> None:
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.database_url == "sqlite:///data/salesos.db"
    assert len(settings.secret_key.get_secret_value()) >= 32


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SALESOS_DATABASE_URL", "sqlite:///outro.db")
    monkeypatch.setenv("SALESOS_PORT", "8123")
    settings = Settings()
    assert settings.database_url == "sqlite:///outro.db"
    assert settings.port == 8123


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.0.10", "::", "exemplo.com"])  # noqa: S104
def test_non_loopback_host_is_rejected(host: str) -> None:
    with pytest.raises(ValidationError, match="loopback"):
        Settings(host=host)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_loopback_hosts_are_accepted(host: str) -> None:
    assert Settings(host=host).host == host


def test_secret_is_random_when_not_configured() -> None:
    first = Settings().secret_key.get_secret_value()
    second = Settings().secret_key.get_secret_value()
    assert first != second


def test_empty_secret_falls_back_to_random(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uma linha `SALESOS_SECRET_KEY=` vazia não pode virar uma chave HMAC vazia."""
    monkeypatch.setenv("SALESOS_SECRET_KEY", "")
    assert len(Settings().secret_key.get_secret_value()) >= 32


def test_short_secret_is_rejected() -> None:
    with pytest.raises(ValidationError, match="32"):
        Settings(secret_key=SecretStr("curto"))


def test_allowed_hosts_cannot_be_widened_by_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SALESOS_ALLOWED_HOSTS", '["*"]')
    assert not hasattr(Settings(), "allowed_hosts")
