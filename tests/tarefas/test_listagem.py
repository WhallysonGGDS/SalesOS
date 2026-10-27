"""Agenda, vencidas (D7) e limites, com o momento atual injetado (dados fictícios)."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.tarefas import service
from salesos.features.tarefas.models import Tarefa
from salesos.features.tarefas.schemas import FiltroTarefas
from tests.tarefas.conftest import PRAZO, nova_oportunidade, nova_tarefa, novo_cliente

UM_MINUTO = timedelta(minutes=1)


def _titulos(itens: list[Tarefa]) -> list[str]:
    return [t.titulo for t in itens]


def test_overdue_is_pending_with_deadline_in_the_past(session: Session) -> None:
    tarefa = nova_tarefa(session)
    assert service.contar_vencidas(session, agora=PRAZO - UM_MINUTO) == 0
    assert not service.esta_vencida(tarefa, PRAZO - UM_MINUTO)
    # No instante exato do prazo ainda não venceu: "anterior ao momento atual" (D7).
    assert service.contar_vencidas(session, agora=PRAZO) == 0
    assert not service.esta_vencida(tarefa, PRAZO)
    # Dentro do mesmo segundo, o marcador da linha e o contador concordam.
    meio_segundo = PRAZO + timedelta(milliseconds=500)
    assert service.contar_vencidas(session, agora=meio_segundo) == 0
    assert not service.esta_vencida(tarefa, meio_segundo)
    assert service.contar_vencidas(session, agora=PRAZO + UM_MINUTO) == 1
    assert service.esta_vencida(tarefa, PRAZO + UM_MINUTO)
    assert _titulos(service.tarefas_vencidas(session, agora=PRAZO + UM_MINUTO)) == [tarefa.titulo]


@pytest.mark.parametrize("acao", ["concluir", "cancelar"])
def test_closed_tasks_are_never_overdue(session: Session, acao: str) -> None:
    tarefa = nova_tarefa(session)
    getattr(service, f"{acao}_tarefa")(session, tarefa.id)
    depois = PRAZO + timedelta(days=30)
    assert service.contar_vencidas(session, agora=depois) == 0
    assert service.tarefas_vencidas(session, agora=depois) == []
    assert not service.esta_vencida(tarefa, depois)


@pytest.mark.parametrize(
    ("gravado", "vencida"),
    [
        pytest.param("2026-11-03 13:00:00", True, id="sem-fracao"),
        pytest.param("2026-11-03 13:00:00.000000", True, id="com-fracao"),
        pytest.param("2026-11-03 13:02:00", False, id="depois-do-agora"),
        pytest.param("banana", False, id="texto-invalido"),
    ],
)
def test_overdue_comparison_is_robust_to_stored_format(
    session: Session, gravado: str, vencida: bool
) -> None:
    tarefa = nova_tarefa(session)
    session.execute(
        text("UPDATE tarefas SET prazo = :p WHERE id = :i"), {"p": gravado, "i": tarefa.id}
    )
    session.commit()
    assert service.contar_vencidas(session, agora=PRAZO + UM_MINUTO) == int(vencida)


def test_agenda_is_ordered_by_deadline_and_filtered(session: Session) -> None:
    cliente_id = novo_cliente(session)
    nova_tarefa(session, cliente_id, titulo="depois", prazo=PRAZO + timedelta(days=2))
    nova_tarefa(session, cliente_id, titulo="antes", prazo=PRAZO, tipo="reuniao", prioridade="alta")
    feita = nova_tarefa(session, cliente_id, titulo="feita", prazo=PRAZO - timedelta(days=1))
    service.concluir_tarefa(session, feita.id)

    def titulos(**filtro: str) -> list[str]:
        f = FiltroTarefas.model_validate(filtro)
        return _titulos(service.listar_tarefas(session, f).itens)

    assert titulos() == ["antes", "depois"]  # padrão: só pendentes, por prazo
    assert titulos(estado="todas") == ["feita", "antes", "depois"]
    assert titulos(estado="concluida") == ["feita"]
    assert titulos(prioridade="alta") == ["antes"]
    assert titulos(tipo="ligacao") == ["depois"]


@pytest.mark.usefixtures("fuso")
def test_period_filter_uses_local_days(session: Session) -> None:
    cliente_id = novo_cliente(session)
    local = timezone(timedelta(hours=-3))
    nova_tarefa(
        session,
        cliente_id,
        titulo="31 23h30 local",
        prazo=datetime(2026, 10, 31, 23, 30, tzinfo=local),
    )
    nova_tarefa(
        session, cliente_id, titulo="1º 00h local", prazo=datetime(2026, 11, 1, 0, 0, tzinfo=local)
    )
    dia_31 = FiltroTarefas(de=date(2026, 10, 31), ate=date(2026, 10, 31))
    assert _titulos(service.listar_tarefas(session, dia_31).itens) == ["31 23h30 local"]
    so_de = FiltroTarefas(de=date(2026, 11, 1))
    assert _titulos(service.listar_tarefas(session, so_de).itens) == ["1º 00h local"]


def test_listings_are_limited(session: Session) -> None:
    cliente_id = novo_cliente(session)
    oportunidade_id = nova_oportunidade(session, cliente_id)
    for i in range(55):
        nova_tarefa(
            session,
            cliente_id,
            titulo=f"t{i:02d}",
            prazo=PRAZO + timedelta(hours=i),
            oportunidade_id=oportunidade_id,
        )
    primeira = service.listar_tarefas(session, FiltroTarefas(), pagina=1)
    terceira = service.listar_tarefas(session, FiltroTarefas(), pagina=3)
    assert (len(primeira.itens), primeira.tem_proxima) == (service.POR_PAGINA, True)
    assert (len(terceira.itens), terceira.tem_proxima) == (15, False)
    assert len(service.tarefas_do_cliente(session, cliente_id)) == service.RELACIONADAS_MAX == 50
    assert len(service.tarefas_da_oportunidade(session, oportunidade_id)) == 50
    assert (
        len(service.tarefas_vencidas(session, agora=PRAZO + timedelta(days=30)))
        == service.POR_PAGINA
    )


def test_related_lists_show_pending_first(session: Session) -> None:
    cliente_id = novo_cliente(session)
    feita = nova_tarefa(session, cliente_id, titulo="feita", prazo=PRAZO - timedelta(days=5))
    service.concluir_tarefa(session, feita.id)
    nova_tarefa(session, cliente_id, titulo="pendente", prazo=PRAZO)
    assert _titulos(service.tarefas_do_cliente(session, cliente_id)) == ["pendente", "feita"]


def test_anonymized_clients_leave_the_counter_and_the_agenda(session: Session) -> None:
    # Decisão do usuário (D10): ninguém consegue fechar essas tarefas (409), então elas não
    # contam como vencidas nem aparecem na agenda; continuam na página do cliente.
    anonimo = novo_cliente(session, "Anonimo Ficticio")
    nova_tarefa(session, anonimo)
    visivel = nova_tarefa(session)
    clientes.anonimizar_cliente(session, anonimo)
    depois = PRAZO + UM_MINUTO
    assert service.contar_vencidas(session, agora=depois) == 1
    assert [t.id for t in service.tarefas_vencidas(session, agora=depois)] == [visivel.id]
    todas = service.listar_tarefas(session, FiltroTarefas(estado="todas")).itens
    assert [t.id for t in todas] == [visivel.id]
    assert len(service.tarefas_do_cliente(session, anonimo)) == 1
