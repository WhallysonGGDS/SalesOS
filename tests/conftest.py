import sys
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
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


# Nomes que o Windows dá ao fuso de Brasília (E. South America): em português e em inglês.
NOMES_BRASILIA = ("Brasil", "Brazil", "E. South America")


def sistema_em_brasilia(nome: str, deslocamento: timedelta) -> bool:
    """O fuso do sistema é o de Brasília? Pelo nome e pelo deslocamento de hoje (-03:00)."""
    return deslocamento == timedelta(hours=-3) and any(n in nome for n in NOMES_BRASILIA)


@pytest.fixture
def fuso(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fuso America/Sao_Paulo para os testes de dia local e de horário de verão histórico.

    No POSIX, fixado no processo com `time.tzset()`. No Windows não existe `tzset`: os testes
    usam o fuso do próprio sistema e só rodam se ele for o de Brasília (P3, E4). Se o Windows
    não tiver as regras de 2018-2019, eles falham ali, e isso é a evidência que faltava.
    """
    if sys.platform == "win32" or not hasattr(time, "tzset"):
        agora = datetime.now().astimezone()
        nome, deslocamento = time.tzname[0], agora.utcoffset() or timedelta(0)
        if not sistema_em_brasilia(nome, deslocamento):
            pytest.skip(f"fuso do sistema não é o de Brasília ({nome}, UTC{agora:%z})")
        yield
        return
    monkeypatch.setenv("TZ", "America/Sao_Paulo")
    time.tzset()
    yield
    monkeypatch.undo()  # devolve o TZ original antes de recarregar o fuso
    time.tzset()
