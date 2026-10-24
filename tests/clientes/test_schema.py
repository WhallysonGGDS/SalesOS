"""Esquema da Fase 02 conferido no banco migrado, só com SQL (dados fictícios)."""

import pytest
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import IntegrityError

ORIGENS = (
    "indicacao",
    "site",
    "instagram",
    "linkedin",
    "whatsapp",
    "evento",
    "prospeccao_ativa",
    "outro",
)


def _cliente(conn: Connection, nome: str = "Cliente Ficticio", **campos: str | None) -> int:
    valores = {"tipo": "PJ", "nome": nome, "origem": "site", "email": None, "documento": None}
    valores.update(campos)
    result = conn.execute(
        text(
            "INSERT INTO clientes (tipo, nome, origem, email, documento) "
            "VALUES (:tipo, :nome, :origem, :email, :documento) RETURNING id"
        ),
        valores,
    )
    return int(result.scalar_one())


def _contato(conn: Connection, cliente_id: int, email: str | None = None) -> int:
    result = conn.execute(
        text(
            "INSERT INTO contatos (cliente_id, nome, email) VALUES (:c, 'Contato Ficticio', :e)"
            " RETURNING id"
        ),
        {"c": cliente_id, "e": email},
    )
    return int(result.scalar_one())


def _interacao(
    conn: Connection, cliente_id: int, tipo: str = "nota", contato_id: int | None = None
) -> int:
    result = conn.execute(
        text(
            "INSERT INTO interacoes (cliente_id, contato_id, tipo, ocorrida_em, resumo) "
            "VALUES (:c, :k, :t, '2026-01-02 03:04:05', 'Resumo ficticio') RETURNING id"
        ),
        {"c": cliente_id, "k": contato_id, "t": tipo},
    )
    return int(result.scalar_one())


def test_tables_exist_with_timestamps_and_defaults(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        row = conn.execute(
            text(
                "SELECT busca, created_at, updated_at, archived_at, anonimizado_em "
                "FROM clientes WHERE id = :id"
            ),
            {"id": cliente_id},
        ).one()
    assert row.busca == ""
    assert row.created_at is not None and row.updated_at is not None
    assert row.archived_at is None and row.anonimizado_em is None


def test_phone_columns_do_not_exist_while_blocked(migrated_engine: Engine) -> None:
    """D12: telefone fica fora do banco até as regras da Anatel serem aprovadas."""
    columns = inspect(migrated_engine)
    for table in ("clientes", "contatos"):
        names = {col["name"] for col in columns.get_columns(table)}
        assert "telefone" not in names


@pytest.mark.parametrize("origem", ORIGENS)
def test_every_approved_origin_is_accepted(migrated_engine: Engine, origem: str) -> None:
    with migrated_engine.begin() as conn:
        _cliente(conn, origem=origem)


@pytest.mark.parametrize(
    ("campo", "valor"), [("origem", "tiktok"), ("origem", ""), ("tipo", "XX"), ("tipo", "pf")]
)
def test_check_constraints_reject_unknown_values(
    migrated_engine: Engine, campo: str, valor: str
) -> None:
    with pytest.raises(IntegrityError, match="CHECK"), migrated_engine.begin() as conn:
        _cliente(conn, **{campo: valor})


def test_interaction_type_is_constrained(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        for tipo in ("ligacao", "reuniao", "mensagem", "email", "nota", "sistema"):
            _interacao(conn, cliente_id, tipo)
    with pytest.raises(IntegrityError, match="CHECK"), migrated_engine.begin() as conn:
        _interacao(conn, cliente_id, "visita")


def test_client_email_and_document_are_unique_but_optional(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        _cliente(conn, email=None)
        _cliente(conn, email=None)
        _cliente(conn, email="vendas@exemplo.com", documento="X1")
    with pytest.raises(IntegrityError, match="UNIQUE"), migrated_engine.begin() as conn:
        _cliente(conn, email="vendas@exemplo.com")
    with pytest.raises(IntegrityError, match="UNIQUE"), migrated_engine.begin() as conn:
        _cliente(conn, documento="X1")


def test_contact_email_unique_only_within_same_client(migrated_engine: Engine) -> None:
    """D2: pode repetir entre clientes, não dentro do mesmo cliente."""
    with migrated_engine.begin() as conn:
        a, b = _cliente(conn, "A"), _cliente(conn, "B")
        _contato(conn, a, "pessoa@exemplo.com")
        _contato(conn, b, "pessoa@exemplo.com")
        _contato(conn, a, None)
        _contato(conn, a, None)
    with pytest.raises(IntegrityError, match="UNIQUE"), migrated_engine.begin() as conn:
        _contato(conn, a, "pessoa@exemplo.com")


def test_unique_constraint_names_list_all_their_columns(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    criadas = {
        uq["name"]: uq["column_names"]
        for tabela in ("clientes", "contatos")
        for uq in inspector.get_unique_constraints(tabela)
    }
    assert criadas == {
        "uq_clientes_documento": ["documento"],
        "uq_clientes_email": ["email"],
        "uq_contatos_cliente_id_email": ["cliente_id", "email"],
    }


def test_client_with_children_cannot_be_deleted(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        _contato(conn, cliente_id)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), migrated_engine.begin() as conn:
        conn.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": cliente_id})


def test_interaction_requires_existing_client(migrated_engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), migrated_engine.begin() as conn:
        _interacao(conn, 999)


def test_removing_contact_keeps_interaction_with_null_reference(migrated_engine: Engine) -> None:
    """D3: remover contato não apaga o histórico; a interação fica sem contato."""
    with migrated_engine.begin() as conn:
        cliente_id = _cliente(conn)
        contato_id = _contato(conn, cliente_id)
        interacao_id = _interacao(conn, cliente_id, contato_id=contato_id)
        conn.execute(text("DELETE FROM contatos WHERE id = :id"), {"id": contato_id})
        restante = conn.execute(
            text("SELECT contato_id FROM interacoes WHERE id = :id"), {"id": interacao_id}
        ).scalar_one()
    assert restante is None
