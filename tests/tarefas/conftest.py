import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from salesos.config import Settings
from salesos.features.clientes import service as clientes
from salesos.features.clientes.schemas import ClienteIn
from salesos.features.oportunidades import service as oportunidades
from salesos.features.oportunidades.schemas import OportunidadeIn
from salesos.features.tarefas import service
from salesos.features.tarefas.models import Tarefa
from salesos.features.tarefas.schemas import TarefaIn
from salesos.main import create_app
from tests.conftest import migrar
from tests.oportunidades.test_routes import _post

PRAZO = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as s:
        yield s


def novo_cliente(session: Session, nome: str = "Empresa Ficticia") -> int:
    return clientes.criar_cliente(session, ClienteIn(tipo="PJ", nome=nome, origem="site")).id


def nova_oportunidade(session: Session, cliente_id: int) -> int:
    dados = OportunidadeIn(titulo="Projeto ficticio")
    return oportunidades.criar_oportunidade(session, cliente_id, dados).id


def nova_tarefa(session: Session, cliente_id: int | None = None, **campos: Any) -> Tarefa:
    dados = {"tipo": "ligacao", "titulo": "Ligar para o cliente", "prazo": PRAZO} | campos
    cliente = cliente_id or novo_cliente(session)
    return service.criar_tarefa(session, cliente, TarefaIn.model_validate(dados))


# --- rotas: banco migrado, aplicação e cliente HTTP com o cookie CSRF ---

PASSADO = "2020-01-01T10:00"
FUTURO = "2099-01-01T10:00"


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
        cliente.get("/tarefas")  # recebe o cookie CSRF
        yield cliente


def _cliente(web: TestClient, nome: str = "Empresa Ficticia") -> int:
    resposta = _post(web, "/clientes", tipo="PJ", nome=nome, origem="site")
    return int(resposta.headers["location"].rsplit("/", 1)[1])


def _oportunidade(web: TestClient, cliente_id: int) -> int:
    resposta = _post(web, "/oportunidades", cliente_id=str(cliente_id), titulo="Projeto")
    return int(resposta.headers["location"].rsplit("/", 1)[1])


def _tarefa(web: TestClient, cliente_id: int | None = None, **campos: str) -> int:
    dados = {
        "cliente_id": str(cliente_id or _cliente(web)),
        "tipo": "ligacao",
        "titulo": "Ligar para o cliente",
        "prazo": FUTURO,
    }
    resposta = _post(web, "/tarefas", **(dados | campos))
    assert resposta.status_code == 303, resposta.text
    match = re.fullmatch(r"/tarefas/(\d+)", resposta.headers["location"])
    assert match is not None
    return int(match.group(1))
