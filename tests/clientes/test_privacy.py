"""Privacidade e anonimização (D4, D9) com valores-sentinela fictícios."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from salesos.features.clientes import service
from salesos.features.clientes.models import Cliente, Contato, Interacao
from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn

SENTINELAS = {
    "nome": "Qwxnomesentinela",
    "nome_fantasia": "Qwxfantasiasentinela",
    "email": "qwx.sentinela@exemplo.com",
    "observacoes": "Qwxobservacaosentinela",
}
CONTATO = {"nome": "Qwxcontatosentinela", "cargo": "Qwxcargosentinela", "email": "qwx@c.com"}
RESUMO = "Qwxresumosentinela"
TODAS = [*SENTINELAS.values(), *CONTATO.values(), RESUMO]


def _cliente_completo(session: Session) -> Cliente:
    cliente = service.criar_cliente(session, ClienteIn(tipo="PJ", origem="indicacao", **SENTINELAS))
    contato = service.adicionar_contato(session, cliente.id, ContatoIn(**CONTATO))
    service.atualizar_contato(session, contato.id, ContatoIn(**{**CONTATO, "cargo": "Outro"}))
    service.registrar_interacao(
        session,
        cliente.id,
        InteracaoIn(
            tipo="reuniao",
            ocorrida_em=datetime(2026, 10, 1, tzinfo=UTC),
            resumo=RESUMO,
            contato_id=contato.id,
        ),
    )
    service.atualizar_cliente(
        session, cliente.id, ClienteIn(tipo="PF", origem="site", **SENTINELAS)
    )
    service.arquivar_cliente(session, cliente.id)
    return cliente


def _bytes_do_banco(engine: Engine) -> bytes:
    caminho = Path(str(engine.url.database))
    partes = [caminho, caminho.with_name(caminho.name + "-wal")]
    return b"".join(p.read_bytes() for p in partes if p.exists()).lower()


def test_events_never_contain_personal_values(session: Session) -> None:
    cliente = _cliente_completo(session)
    eventos = session.scalars(
        select(Interacao.resumo).where(
            Interacao.cliente_id == cliente.id, Interacao.tipo == "sistema"
        )
    ).all()
    assert len(eventos) == 5
    texto = " ".join(eventos).lower()
    assert not [s for s in TODAS if s.lower() in texto]


def test_logs_never_contain_personal_values(
    session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    cliente = _cliente_completo(session)
    service.anonimizar_cliente(session, cliente.id)
    texto = caplog.text.lower()
    assert not [s for s in TODAS if s.lower() in texto]


def test_anonymization_replaces_data_and_keeps_references(session: Session) -> None:
    cliente = _cliente_completo(session)
    total_antes = session.execute(
        select(func.count()).where(Interacao.cliente_id == cliente.id)
    ).scalar_one()
    service.anonimizar_cliente(session, cliente.id)
    session.refresh(cliente)

    assert cliente.nome == f"Cliente anonimizado #{cliente.id}"
    assert (cliente.nome_fantasia, cliente.email, cliente.observacoes, cliente.documento) == (
        None,
        None,
        None,
        None,
    )
    assert cliente.busca == f"cliente anonimizado #{cliente.id}"
    assert cliente.anonimizado_em is not None and cliente.archived_at is not None
    assert session.scalars(select(Contato).where(Contato.cliente_id == cliente.id)).all() == []

    interacoes = session.scalars(
        select(Interacao).where(Interacao.cliente_id == cliente.id).order_by(Interacao.id)
    ).all()
    assert len(interacoes) == total_antes + 1
    reuniao = next(i for i in interacoes if i.tipo == "reuniao")
    assert (reuniao.resumo, reuniao.contato_id) == ("[conteúdo removido]", None)
    assert reuniao.ocorrida_em == datetime(2026, 10, 1)
    assert interacoes[-1].resumo == "Cliente anonimizado"
    assert session.execute(text("PRAGMA foreign_key_check")).all() == []


def test_anonymization_is_idempotent(session: Session) -> None:
    cliente = _cliente_completo(session)
    service.anonimizar_cliente(session, cliente.id)
    total = session.scalar(select(func.count()).where(Interacao.cliente_id == cliente.id))
    service.anonimizar_cliente(session, cliente.id)
    assert session.scalar(select(func.count()).where(Interacao.cliente_id == cliente.id)) == total


def test_anonymized_client_refuses_changes(session: Session) -> None:
    cliente = _cliente_completo(session)
    service.anonimizar_cliente(session, cliente.id)
    dados = ClienteIn(tipo="PJ", nome="Volta", origem="site")
    interacao = InteracaoIn(tipo="nota", ocorrida_em=datetime.now(UTC), resumo="x")
    with pytest.raises(service.Bloqueado):
        service.atualizar_cliente(session, cliente.id, dados)
    with pytest.raises(service.Bloqueado):
        service.desarquivar_cliente(session, cliente.id)
    with pytest.raises(service.Bloqueado):
        service.adicionar_contato(session, cliente.id, ContatoIn(nome="Pessoa"))
    with pytest.raises(service.Bloqueado):
        service.registrar_interacao(session, cliente.id, interacao)


def test_old_data_is_not_searchable_after_anonymization(session: Session) -> None:
    cliente = _cliente_completo(session)
    service.anonimizar_cliente(session, cliente.id)
    for termo in (SENTINELAS["nome"], SENTINELAS["nome_fantasia"], SENTINELAS["email"]):
        assert service.listar_clientes(session, termo, arquivados=True).itens == []


def test_database_files_do_not_keep_personal_bytes(
    session: Session, migrated_engine: Engine
) -> None:
    cliente = _cliente_completo(session)
    antes = _bytes_do_banco(migrated_engine)
    assert all(s.lower().encode() in antes for s in TODAS if s != CONTATO["cargo"])

    service.anonimizar_cliente(session, cliente.id)
    depois = _bytes_do_banco(migrated_engine)
    assert [s for s in TODAS if s.lower().encode() in depois] == []
