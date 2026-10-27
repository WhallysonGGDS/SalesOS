"""Regras das tarefas (D1, D5, D6, D8) e histórico só de acréscimo, com dados fictícios."""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.clientes.models import Interacao
from salesos.features.tarefas import service
from salesos.features.tarefas.models import Tarefa, TarefaEvento
from salesos.features.tarefas.schemas import TarefaIn
from salesos.formularios import RegraViolada
from tests.tarefas.conftest import PRAZO, nova_oportunidade, nova_tarefa, novo_cliente


def _historico(session: Session, tarefa: Tarefa) -> list[tuple[Any, ...]]:
    linhas = session.execute(
        select(TarefaEvento.id, TarefaEvento.acao, TarefaEvento.ocorrida_em)
        .where(TarefaEvento.tarefa_id == tarefa.id)
        .order_by(TarefaEvento.id)
    )
    return [tuple(linha) for linha in linhas]


def _eventos_cliente(session: Session, cliente_id: int) -> list[str]:
    query = select(Interacao.resumo).where(
        Interacao.cliente_id == cliente_id, Interacao.tipo == "sistema"
    )
    return [e for e in session.scalars(query.order_by(Interacao.id)) if e.startswith("Tarefa")]


def _contagens(session: Session) -> tuple[int, int, int]:
    return (
        session.scalar(select(func.count()).select_from(Tarefa)) or 0,
        session.scalar(select(func.count()).select_from(TarefaEvento)) or 0,
        session.scalar(select(func.count()).select_from(Interacao)) or 0,
    )


def test_creation_records_history_and_client_event(session: Session) -> None:
    tarefa = nova_tarefa(session)
    assert (tarefa.estado, tarefa.prioridade, tarefa.concluida_em) == ("pendente", "normal", None)
    assert [a for _i, a, _q in _historico(session, tarefa)] == ["criada"]
    assert _eventos_cliente(session, tarefa.cliente_id) == [f"Tarefa #{tarefa.id} criada"]


def test_opportunity_must_belong_to_the_same_client(session: Session) -> None:
    cliente_id = novo_cliente(session)
    propria = nova_oportunidade(session, cliente_id)
    alheia = nova_oportunidade(session, novo_cliente(session, "Outra Empresa"))
    assert nova_tarefa(session, cliente_id, oportunidade_id=propria).oportunidade_id == propria
    antes = _contagens(session)
    for oportunidade_id in (alheia, 999_999):
        with pytest.raises(RegraViolada) as erro:
            nova_tarefa(session, cliente_id, oportunidade_id=oportunidade_id)
        assert erro.value.campo == "oportunidade_id"
        session.rollback()
    assert _contagens(session) == antes
    tarefa = nova_tarefa(session, cliente_id)
    dados = TarefaIn(tipo="ligacao", titulo="X", prazo=PRAZO, oportunidade_id=alheia)
    with pytest.raises(RegraViolada):
        service.atualizar_tarefa(session, tarefa.id, dados)


def test_missing_client_is_not_found(session: Session) -> None:
    with pytest.raises(clientes.NaoEncontrado):
        service.criar_tarefa(session, 999, TarefaIn(tipo="ligacao", titulo="X", prazo=PRAZO))


@pytest.mark.parametrize(("acao", "estado"), [("concluir", "concluida"), ("cancelar", "cancelada")])
def test_close_and_reopen_keep_history(session: Session, acao: str, estado: str) -> None:
    tarefa = nova_tarefa(session)
    getattr(service, f"{acao}_tarefa")(session, tarefa.id)
    session.refresh(tarefa)
    assert tarefa.estado == estado
    assert (tarefa.concluida_em is not None) == (estado == "concluida")
    assert (tarefa.cancelada_em is not None) == (estado == "cancelada")
    historico = _historico(session, tarefa)

    service.reabrir_tarefa(session, tarefa.id)
    session.refresh(tarefa)
    assert (tarefa.estado, tarefa.concluida_em, tarefa.cancelada_em) == ("pendente", None, None)
    depois = _historico(session, tarefa)
    assert depois[: len(historico)] == historico
    assert [a for _i, a, _q in depois] == ["criada", estado, "reaberta"]
    assert _eventos_cliente(session, tarefa.cliente_id)[1:] == [
        f"Tarefa #{tarefa.id} {'concluída' if estado == 'concluida' else 'cancelada'}",
        f"Tarefa #{tarefa.id} reaberta",
    ]


def test_repeating_the_current_state_creates_nothing(session: Session) -> None:
    tarefa = nova_tarefa(session)
    service.reabrir_tarefa(session, tarefa.id)  # já pendente
    service.concluir_tarefa(session, tarefa.id)
    session.refresh(tarefa)
    concluida_em = tarefa.concluida_em
    antes = _contagens(session)
    service.concluir_tarefa(session, tarefa.id)  # envio duplo
    session.refresh(tarefa)
    assert _contagens(session) == antes
    assert tarefa.concluida_em == concluida_em


@pytest.mark.parametrize(
    ("primeiro", "depois"), [("concluir", "cancelar"), ("cancelar", "concluir")]
)
def test_closed_to_closed_requires_reopening(session: Session, primeiro: str, depois: str) -> None:
    tarefa = nova_tarefa(session)
    getattr(service, f"{primeiro}_tarefa")(session, tarefa.id)
    antes = _contagens(session)
    with pytest.raises(RegraViolada, match="Reabra a tarefa antes de mudar o estado"):
        getattr(service, f"{depois}_tarefa")(session, tarefa.id)
    session.rollback()
    assert _contagens(session) == antes


def test_only_pending_tasks_can_be_edited(session: Session) -> None:
    tarefa = nova_tarefa(session)
    dados = TarefaIn(tipo="reuniao", titulo="Reunião", prazo=PRAZO, prioridade="alta")
    service.atualizar_tarefa(session, tarefa.id, dados)
    service.atualizar_tarefa(session, tarefa.id, dados)  # sem mudança: sem evento
    assert _eventos_cliente(session, tarefa.cliente_id)[1:] == [
        f"Tarefa #{tarefa.id} atualizada: prioridade, tipo, titulo"
    ]
    for acao in ("concluir", "cancelar"):
        getattr(service, f"{acao}_tarefa")(session, tarefa.id)
        with pytest.raises(RegraViolada, match="pendente"):
            service.atualizar_tarefa(session, tarefa.id, dados)
        session.rollback()
        service.reabrir_tarefa(session, tarefa.id)


def test_archived_client_accepts_and_anonymized_refuses(session: Session) -> None:
    tarefa = nova_tarefa(session)
    clientes.arquivar_cliente(session, tarefa.cliente_id)
    service.concluir_tarefa(session, tarefa.id)
    clientes.anonimizar_cliente(session, tarefa.cliente_id)
    dados = TarefaIn(tipo="ligacao", titulo="X", prazo=PRAZO)
    operacoes: list[Callable[[], object]] = [
        lambda: service.criar_tarefa(session, tarefa.cliente_id, dados),
        lambda: service.atualizar_tarefa(session, tarefa.id, dados),
        lambda: service.reabrir_tarefa(session, tarefa.id),
        lambda: service.concluir_tarefa(session, tarefa.id),
        lambda: service.cancelar_tarefa(session, tarefa.id),
    ]
    for operacao in operacoes:
        with pytest.raises(clientes.Bloqueado):
            operacao()


def test_event_failure_rolls_back_the_whole_operation(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarefa = nova_tarefa(session)
    fechada = nova_tarefa(session, tarefa.cliente_id)
    service.concluir_tarefa(session, fechada.id)
    antes = _contagens(session)

    def falhar(*_a: Any) -> None:
        raise RuntimeError("falha injetada")

    monkeypatch.setattr(service, "registrar_evento", falhar)
    operacoes: list[Callable[[], object]] = [
        lambda: service.concluir_tarefa(session, tarefa.id),
        lambda: service.reabrir_tarefa(session, fechada.id),
        lambda: service.atualizar_tarefa(
            session, tarefa.id, TarefaIn(tipo="reuniao", titulo="Y", prazo=PRAZO)
        ),
        lambda: service.criar_tarefa(
            session, tarefa.cliente_id, TarefaIn(tipo="ligacao", titulo="X", prazo=PRAZO)
        ),
    ]
    for operacao in operacoes:
        with pytest.raises(RuntimeError):
            operacao()
        session.rollback()
        assert _contagens(session) == antes
    assert session.get(Tarefa, tarefa.id).estado == "pendente"  # type: ignore[union-attr]
    assert session.get(Tarefa, tarefa.id).tipo == "ligacao"  # type: ignore[union-attr]
    assert session.get(Tarefa, fechada.id).estado == "concluida"  # type: ignore[union-attr]


def test_history_is_never_rewritten(session: Session) -> None:
    tarefa = nova_tarefa(session)
    passos: list[Callable[[], object]] = [
        lambda: service.concluir_tarefa(session, tarefa.id),
        lambda: service.reabrir_tarefa(session, tarefa.id),
        lambda: service.cancelar_tarefa(session, tarefa.id),
        lambda: service.reabrir_tarefa(session, tarefa.id),
        lambda: service.atualizar_tarefa(
            session, tarefa.id, TarefaIn(tipo="retorno", titulo="Novo", prazo=PRAZO)
        ),
        lambda: clientes.anonimizar_cliente(session, tarefa.cliente_id),
    ]
    for passo in passos:
        visto = _historico(session, tarefa)
        passo()
        session.expire_all()
        assert _historico(session, tarefa)[: len(visto)] == visto
    assert [a for _i, a, _q in _historico(session, tarefa)] == [
        "criada",
        "concluida",
        "reaberta",
        "cancelada",
        "reaberta",
    ]
    publicas = {n for n in dir(service) if not n.startswith("_")}
    assert not {n for n in publicas if "evento" in n} - {"eventos", "registrar_evento"}
