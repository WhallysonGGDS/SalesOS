from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from salesos.config import Settings
from salesos.main import create_app
from tests.conftest import migrar


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as s:
        yield s


@pytest.fixture
def db(tmp_path: Path) -> Path:
    caminho = tmp_path / "teste.db"
    migrar(caminho)
    return caminho


@pytest.fixture
def web_app(db: Path, settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def web(web_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(web_app, base_url="http://127.0.0.1") as cliente:
        cliente.get("/clientes")  # recebe o cookie CSRF
        yield cliente
