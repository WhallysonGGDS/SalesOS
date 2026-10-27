from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from salesos.features.tarefas.schemas import TarefaIn
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.clientes.schemas import ClienteIn
from salesos.features.oportunidades import service as oportunidades
from salesos.features.oportunidades.schemas import OportunidadeIn
from salesos.features.tarefas import service
from salesos.features.tarefas.models import Tarefa

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
