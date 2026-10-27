"""Privacidade das tarefas (D6, D10) com valores-sentinela fictícios."""

from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.clientes.models import Interacao
from salesos.features.tarefas import service
from salesos.features.tarefas.models import Tarefa, TarefaEvento
from salesos.features.tarefas.schemas import TarefaIn
from tests.tarefas.conftest import PRAZO, nova_tarefa

TITULO = "Qwxtarefasentinela"
DESCRICAO = "Qwxdescricaosentinela"


def _percorrer(session: Session) -> Tarefa:
    tarefa = nova_tarefa(session, titulo=TITULO, descricao=DESCRICAO)
    service.concluir_tarefa(session, tarefa.id)
    service.reabrir_tarefa(session, tarefa.id)
    dados = TarefaIn(tipo="reuniao", titulo=TITULO, descricao=DESCRICAO, prazo=PRAZO)
    service.atualizar_tarefa(session, tarefa.id, dados)
    return tarefa


def _bytes_do_banco(engine: Engine) -> bytes:
    caminho = Path(str(engine.url.database))
    partes = [caminho, caminho.with_name(caminho.name + "-wal")]
    return b"".join(p.read_bytes() for p in partes if p.exists()).lower()


def test_client_events_never_contain_title_or_description(session: Session) -> None:
    tarefa = _percorrer(session)
    eventos = session.scalars(
        select(Interacao.resumo).where(Interacao.cliente_id == tarefa.cliente_id)
    )
    texto = " ".join(eventos).lower()
    assert TITULO.lower() not in texto and DESCRICAO.lower() not in texto


def test_anonymization_erases_text_and_keeps_history(
    session: Session, migrated_engine: Engine
) -> None:
    tarefa = _percorrer(session)
    historico = session.execute(select(TarefaEvento.id, TarefaEvento.acao)).all()
    antes = _bytes_do_banco(migrated_engine)
    assert TITULO.lower().encode() in antes and DESCRICAO.lower().encode() in antes

    clientes.anonimizar_cliente(session, tarefa.cliente_id)
    session.refresh(tarefa)

    assert (tarefa.titulo, tarefa.descricao) == (f"Tarefa #{tarefa.id}", None)
    assert (tarefa.tipo, tarefa.estado, tarefa.prazo is not None) == ("reuniao", "pendente", True)
    assert session.execute(select(TarefaEvento.id, TarefaEvento.acao)).all() == historico
    depois = _bytes_do_banco(migrated_engine)
    assert TITULO.lower().encode() not in depois and DESCRICAO.lower().encode() not in depois
