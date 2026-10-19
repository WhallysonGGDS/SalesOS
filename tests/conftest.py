from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from salesos.config import Settings
from salesos.main import create_app

TEST_SECRET = "segredo-de-teste-com-mais-de-32-caracteres"


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Nenhum teste lê o .env nem as variáveis SALESOS_* reais, nem escreve na pasta do projeto."""
    for name in ("SALESOS_HOST", "SALESOS_PORT", "SALESOS_DATABASE_URL", "SALESOS_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'teste.db'}",
        secret_key=SecretStr(TEST_SECRET),
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client
