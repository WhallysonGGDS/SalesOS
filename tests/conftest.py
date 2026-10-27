import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from salesos.config import Settings
from salesos.db import create_db_engine
from salesos.main import create_app

TEST_SECRET = "segredo-de-teste-com-mais-de-32-caracteres"
ROOT = Path(__file__).resolve().parents[1]


def migrar(db: Path, revisao: str = "head") -> None:
    """Aplica as migrações reais num banco temporário (nunca o banco do projeto)."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    command.upgrade(config, revisao)


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Nenhum teste lê o .env nem as variáveis SALESOS_* reais, nem escreve na pasta do projeto."""
    for name in (
        "SALESOS_HOST",
        "SALESOS_PORT",
        "SALESOS_DATABASE_URL",
        "SALESOS_SECRET_KEY",
        "SALESOS_BACKUP_DIR",
    ):
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


@pytest.fixture
def migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    """Banco temporário migrado até o head pelo Alembic real."""
    db = tmp_path / "clientes.db"
    migrar(db)
    engine = create_db_engine(f"sqlite:///{db}")
    yield engine
    engine.dispose()


@pytest.fixture
def fuso(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fixa o fuso do processo em America/Sao_Paulo (só POSIX: o Windows não tem tzset)."""
    if sys.platform == "win32" or not hasattr(time, "tzset"):
        pytest.skip("time.tzset só existe em POSIX; fuso histórico não verificado no Windows")
    monkeypatch.setenv("TZ", "America/Sao_Paulo")
    time.tzset()
    yield
    monkeypatch.undo()  # devolve o TZ original antes de recarregar o fuso
    time.tzset()
