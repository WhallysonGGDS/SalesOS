"""Esquema da Fase 04 conferido com SQL direto no banco migrado (dados fictícios)."""

from typing import Any

import pytest
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import IntegrityError

PRAZO = "2026-11-03 13:00:00"
QUANDO = "2026-11-02 10:00:00"


def _cliente(conn: Connection) -> int:
    sql = "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', 'Cliente Ficticio', 'site')"
    return int(conn.execute(text(sql + " RETURNING id")).scalar_one())


def _oportunidade(conn: Connection, cliente_id: int) -> int:
    sql = (
        "INSERT INTO oportunidades (cliente_id, titulo, etapa) "
        "VALUES (:c, 'Projeto ficticio', 'novo_lead') RETURNING id"
    )
    return int(conn.execute(text(sql), {"c": cliente_id}).scalar_one())


def _tarefa(conn: Connection, cliente_id: int, **campos: Any) -> int:
    valores: dict[str, Any] = {
        "cliente_id": cliente_id,
        "oportunidade_id": None,
        "tipo": "ligacao",
        "titulo": "Ligar para o cliente ficticio",
        "prazo": PRAZO,
        "estado": "pendente",
        "concluida_em": None,
        "cancelada_em": None,
    } | campos
    colunas = ", ".join(valores)
    marcadores = ", ".join(f":{c}" for c in valores)
    sql = f"INSERT INTO tarefas ({colunas}) VALUES ({marcadores}) RETURNING id"  # noqa: S608
    return int(conn.execute(text(sql), valores).scalar_one())


def _evento(conn: Connection, tarefa_id: int, acao: str) -> None:
    conn.execute(
        text("INSERT INTO tarefa_eventos (tarefa_id, acao, ocorrida_em) VALUES (:t, :a, :q)"),
        {"t": tarefa_id, "a": acao, "q": QUANDO},
    )


def test_defaults_and_indexes(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        tarefa_id = _tarefa(conn, _cliente(conn))
        _evento(conn, tarefa_id, "criada")
        row = conn.execute(
            text("SELECT prioridade, estado, created_at, updated_at FROM tarefas WHERE id = :i"),
            {"i": tarefa_id},
        ).one()
        indices = {i["name"] for i in inspect(conn).get_indexes("tarefas")}
    assert (row.prioridade, row.estado) == ("normal", "pendente")
    assert row.created_at is not None and row.updated_at is not None
    assert {
        "ix_tarefas_estado_prazo",
        "ix_tarefas_cliente_id",
        "ix_tarefas_oportunidade_id",
    } <= indices


@pytest.mark.parametrize("tipo", ["ligacao", "reuniao", "mensagem", "retorno"])
@pytest.mark.parametrize("prioridade", ["baixa", "normal", "alta"])
def test_valid_types_and_priorities(migrated_engine: Engine, tipo: str, prioridade: str) -> None:
    with migrated_engine.begin() as conn:
        _tarefa(conn, _cliente(conn), tipo=tipo, prioridade=prioridade)


def test_valid_states_with_their_dates_and_optional_opportunity(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        _tarefa(conn, cliente_id, estado="concluida", concluida_em=QUANDO)
        _tarefa(conn, cliente_id, estado="cancelada", cancelada_em=QUANDO)
        _tarefa(conn, cliente_id, oportunidade_id=_oportunidade(conn, cliente_id))


@pytest.mark.parametrize(
    "campos",
    [
        pytest.param({"tipo": "email"}, id="tipo-fora-da-lista"),
        pytest.param({"prioridade": "urgente"}, id="prioridade-fora-da-lista"),
        pytest.param({"estado": "atrasada"}, id="estado-fora-da-lista"),
        pytest.param({"estado": "concluida"}, id="concluida-sem-data"),
        pytest.param({"estado": "cancelada"}, id="cancelada-sem-data"),
        pytest.param({"concluida_em": QUANDO}, id="pendente-com-data-de-conclusao"),
        pytest.param({"cancelada_em": QUANDO}, id="pendente-com-data-de-cancelamento"),
        pytest.param(
            {"estado": "concluida", "concluida_em": QUANDO, "cancelada_em": QUANDO},
            id="concluida-e-cancelada",
        ),
        pytest.param({"prazo": None}, id="sem-prazo"),
        pytest.param({"titulo": None}, id="sem-titulo"),
    ],
)
def test_invalid_rows_are_refused_by_the_database(
    migrated_engine: Engine, campos: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _tarefa(conn, _cliente(conn), **campos)


def test_event_actions(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        tarefa_id = _tarefa(conn, _cliente(conn))
        for acao in ("criada", "concluida", "reaberta", "cancelada"):
            _evento(conn, tarefa_id, acao)
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _evento(conn, tarefa_id, "editada")


def test_foreign_keys_protect_tasks_and_history(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        oportunidade_id = _oportunidade(conn, cliente_id)
        tarefa_id = _tarefa(conn, cliente_id, oportunidade_id=oportunidade_id)
        _evento(conn, tarefa_id, "criada")
    with migrated_engine.begin() as conn:
        so_com_tarefa = _cliente(conn)  # sem oportunidade: só a FK de tarefas pode recusar
        _tarefa(conn, so_com_tarefa)
    for sql, ident in [
        ("DELETE FROM clientes WHERE id = :i", so_com_tarefa),
        ("DELETE FROM oportunidades WHERE id = :i", oportunidade_id),
        ("DELETE FROM tarefas WHERE id = :i", tarefa_id),
    ]:
        with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
            conn.execute(text(sql), {"i": ident})
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _tarefa(conn, 999_999)
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _tarefa(conn, cliente_id, oportunidade_id=999_999)
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _evento(conn, 999_999, "criada")
