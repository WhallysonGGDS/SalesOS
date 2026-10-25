"""Esquema da Fase 03 conferido com SQL direto no banco migrado (dados fictícios)."""

from typing import Any

import pytest
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import IntegrityError

ABERTAS = ("novo_lead", "qualificacao", "proposta_enviada", "negociacao")
MOTIVOS = ("preco", "concorrente", "sem_orcamento", "sem_resposta", "adiado", "outro")
FECHADA = "2026-10-20 15:00:00"


def _cliente(conn: Connection) -> int:
    sql = "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', 'Cliente Ficticio', 'site')"
    return int(conn.execute(text(sql + " RETURNING id")).scalar_one())


def _oportunidade(conn: Connection, cliente_id: int, **campos: Any) -> int:
    valores: dict[str, Any] = {
        "cliente_id": cliente_id,
        "titulo": "Projeto ficticio",
        "etapa": "novo_lead",
        "valor_centavos": None,
        "fechada_em": None,
        "motivo_perda": None,
    } | campos
    result = conn.execute(
        text(
            "INSERT INTO oportunidades (cliente_id, titulo, etapa, valor_centavos, fechada_em, "
            "motivo_perda) VALUES (:cliente_id, :titulo, :etapa, :valor_centavos, :fechada_em, "
            ":motivo_perda) RETURNING id"
        ),
        valores,
    )
    return int(result.scalar_one())


def _movimentacao(conn: Connection, oportunidade_id: int, de: str | None, para: str) -> None:
    conn.execute(
        text(
            "INSERT INTO movimentacoes (oportunidade_id, de_etapa, para_etapa, ocorrida_em) "
            "VALUES (:o, :de, :para, '2026-10-20 15:00:00')"
        ),
        {"o": oportunidade_id, "de": de, "para": para},
    )


def _recusa(engine: Engine, **campos: Any) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _oportunidade(conn, _cliente(conn), **campos)


def test_tables_have_defaults_and_indexes(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        oportunidade_id = _oportunidade(conn, _cliente(conn))
        _movimentacao(conn, oportunidade_id, None, "novo_lead")
        row = conn.execute(
            text("SELECT created_at, updated_at FROM oportunidades WHERE id = :i"),
            {"i": oportunidade_id},
        ).one()
        assert row.created_at is not None and row.updated_at is not None
        indices = {i["name"] for i in inspect(conn).get_indexes("oportunidades")}
    assert {
        "ix_oportunidades_etapa_created_at",
        "ix_oportunidades_cliente_id",
        "ix_oportunidades_fechada_em",
    } <= indices


@pytest.mark.parametrize("etapa", ABERTAS)
def test_open_stages_are_accepted_without_closing_data(migrated_engine: Engine, etapa: str) -> None:
    with migrated_engine.begin() as conn:
        _oportunidade(conn, _cliente(conn), etapa=etapa)


def test_won_and_lost_are_accepted_with_closing_data(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        _oportunidade(conn, cliente_id, etapa="ganha", valor_centavos=1, fechada_em=FECHADA)
        for motivo in MOTIVOS:
            _oportunidade(
                conn, cliente_id, etapa="perdida", fechada_em=FECHADA, motivo_perda=motivo
            )


@pytest.mark.parametrize(
    "campos",
    [
        pytest.param({"etapa": "contrato"}, id="etapa-invalida"),
        pytest.param({"etapa": "novo_lead", "fechada_em": FECHADA}, id="aberta-com-fechamento"),
        pytest.param({"etapa": "ganha", "valor_centavos": 10}, id="ganha-sem-fechamento"),
        pytest.param({"etapa": "ganha", "fechada_em": FECHADA}, id="ganha-valor-nulo"),
        pytest.param(
            {"etapa": "ganha", "fechada_em": FECHADA, "valor_centavos": 0}, id="ganha-valor-zero"
        ),
        pytest.param({"etapa": "perdida", "fechada_em": FECHADA}, id="perdida-sem-motivo"),
        pytest.param(
            {"etapa": "perdida", "fechada_em": FECHADA, "motivo_perda": "caro"},
            id="motivo-invalido",
        ),
        pytest.param({"motivo_perda": "preco"}, id="motivo-sem-perda"),
        pytest.param({"valor_centavos": -1}, id="valor-negativo"),
        pytest.param({"valor_centavos": 10**12 + 1}, id="valor-acima-do-teto"),
        pytest.param({"valor_centavos": 0.5}, id="valor-fracionario"),
        pytest.param({"valor_centavos": "dez"}, id="valor-texto"),
        pytest.param({"etapa": "perdida", "motivo_perda": "preco"}, id="perdida-sem-fechamento"),
    ],
)
def test_invalid_rows_are_refused_by_the_database(
    migrated_engine: Engine, campos: dict[str, Any]
) -> None:
    _recusa(migrated_engine, **campos)


def test_value_limits_are_accepted(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        _oportunidade(conn, cliente_id, valor_centavos=0)
        _oportunidade(conn, cliente_id, valor_centavos=10**12)


def test_movement_rules(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        oportunidade_id = _oportunidade(conn, _cliente(conn))
        _movimentacao(conn, oportunidade_id, None, "novo_lead")
        _movimentacao(conn, oportunidade_id, "novo_lead", "ganha")
    for de, para in [("novo_lead", "novo_lead"), (None, "contrato"), ("contrato", "ganha")]:
        with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
            _movimentacao(conn, oportunidade_id, de, para)


def test_foreign_keys_protect_history(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        oportunidade_id = _oportunidade(conn, cliente_id)
        _movimentacao(conn, oportunidade_id, None, "novo_lead")
    comandos = [
        ("DELETE FROM clientes WHERE id = :i", cliente_id),
        ("DELETE FROM oportunidades WHERE id = :i", oportunidade_id),
    ]
    for sql, ident in comandos:
        with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
            conn.execute(text(sql), {"i": ident})
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _oportunidade(conn, 999_999)
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        _movimentacao(conn, 999_999, None, "novo_lead")
