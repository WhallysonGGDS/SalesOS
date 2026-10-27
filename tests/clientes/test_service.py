"""Serviços de clientes, contatos e interações (dados fictícios, banco temporário)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from salesos.features.clientes import service
from salesos.features.clientes.models import Cliente, Interacao
from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn


def _cliente(session: Session, nome: str = "Empresa Ficticia", **campos: str) -> Cliente:
    dados = ClienteIn(**{"tipo": "PJ", "nome": nome, "origem": "site", **campos})
    return service.criar_cliente(session, dados)


def _eventos(session: Session, cliente_id: int) -> list[str]:
    query = (
        select(Interacao.resumo)
        .where(Interacao.cliente_id == cliente_id, Interacao.tipo == "sistema")
        .order_by(Interacao.id)
    )
    return list(session.scalars(query))


def _interacao(resumo: str = "Conversa ficticia", **campos: object) -> InteracaoIn:
    padrao = {"tipo": "ligacao", "ocorrida_em": datetime(2026, 10, 1, tzinfo=UTC)}
    return InteracaoIn.model_validate(padrao | {"resumo": resumo} | campos)


def test_create_persists_search_key_and_event(session: Session) -> None:
    cliente = _cliente(session, "José Ação", nome_fantasia="Café", email="Jose@Exemplo.com")
    assert cliente.id is not None
    assert cliente.busca == "jose acao cafe jose@exemplo.com"
    assert _eventos(session, cliente.id) == ["Cliente criado"]


def test_get_missing_client_raises(session: Session) -> None:
    with pytest.raises(service.NaoEncontrado):
        service.obter_cliente(session, 999)


def test_duplicate_email_is_refused_even_when_archived(session: Session) -> None:
    arquivado = _cliente(session, "A", email="vendas@exemplo.com")
    service.arquivar_cliente(session, arquivado.id)
    with pytest.raises(service.Duplicado):
        _cliente(session, "B", email="  VENDAS@exemplo.com ")


def test_email_of_anonymized_client_can_be_reused(session: Session) -> None:
    antigo = _cliente(session, "A", email="vendas@exemplo.com")
    service.anonimizar_cliente(session, antigo.id)
    assert _cliente(session, "B", email="vendas@exemplo.com").email == "vendas@exemplo.com"


def test_update_records_changed_field_names_only(session: Session) -> None:
    cliente = _cliente(session, "Antigo", email="a@exemplo.com")
    novo = ClienteIn(tipo="PJ", nome="Novo", origem="evento", email="a@exemplo.com")
    atualizado = service.atualizar_cliente(session, cliente.id, novo)
    assert atualizado.nome == "Novo"
    assert atualizado.busca == "novo a@exemplo.com"
    service.atualizar_cliente(session, cliente.id, novo)  # sem mudança: sem evento
    assert _eventos(session, cliente.id) == [
        "Cliente criado",
        "Cliente atualizado: nome, origem",
    ]


def test_update_to_email_of_other_client_is_refused(session: Session) -> None:
    _cliente(session, "A", email="a@exemplo.com")
    b = _cliente(session, "B", email="b@exemplo.com")
    with pytest.raises(service.Duplicado):
        service.atualizar_cliente(
            session, b.id, ClienteIn(tipo="PJ", nome="B", origem="site", email="a@exemplo.com")
        )


def test_search_ignores_accents_case_and_like_wildcards(session: Session) -> None:
    _cliente(session, "José da Silva")
    _cliente(session, "Maria 100% Sul")
    _cliente(session, "Outra")
    assert [c.nome for c in service.listar_clientes(session, "JOSE").itens] == ["José da Silva"]
    assert [c.nome for c in service.listar_clientes(session, "0%").itens] == ["Maria 100% Sul"]
    assert [c.nome for c in service.listar_clientes(session, "%").itens] == ["Maria 100% Sul"]
    assert service.listar_clientes(session, "_").itens == []


def test_list_paginates_sorted_by_name(session: Session) -> None:
    for i in range(25):
        _cliente(session, f"Cliente {i:02d}")
    primeira = service.listar_clientes(session, por_pagina=20)
    segunda = service.listar_clientes(session, pagina=2, por_pagina=20)
    assert len(primeira.itens) == 20 and primeira.tem_proxima
    assert [c.nome for c in segunda.itens] == [f"Cliente {i}" for i in range(20, 25)]
    assert not segunda.tem_proxima


def test_list_caps_page_size(session: Session) -> None:
    for i in range(101):
        _cliente(session, f"C{i:03d}")
    assert len(service.listar_clientes(session, por_pagina=10_000).itens) == 100
    assert service.listar_clientes(session, pagina=0).pagina == 1


def test_archive_hides_from_default_list_and_unarchive_returns(session: Session) -> None:
    ativo, arquivado = _cliente(session, "Ativo"), _cliente(session, "Arquivado")
    service.arquivar_cliente(session, arquivado.id)
    assert [c.id for c in service.listar_clientes(session).itens] == [ativo.id]
    assert [c.id for c in service.listar_clientes(session, arquivados=True).itens] == [arquivado.id]
    service.desarquivar_cliente(session, arquivado.id)
    assert service.obter_cliente(session, arquivado.id).archived_at is None
    assert _eventos(session, arquivado.id) == [
        "Cliente criado",
        "Cliente arquivado",
        "Cliente desarquivado",
    ]


def test_contact_email_unique_within_client_only(session: Session) -> None:
    a, b = _cliente(session, "A"), _cliente(session, "B")
    service.adicionar_contato(session, a.id, ContatoIn(nome="P1", email="p@exemplo.com"))
    service.adicionar_contato(session, b.id, ContatoIn(nome="P2", email="p@exemplo.com"))
    with pytest.raises(service.Duplicado):
        service.adicionar_contato(session, a.id, ContatoIn(nome="P3", email="P@exemplo.com "))


def test_contact_update_and_removal_events_have_no_values(session: Session) -> None:
    cliente = _cliente(session)
    contato = service.adicionar_contato(session, cliente.id, ContatoIn(nome="Pessoa"))
    service.atualizar_contato(session, contato.id, ContatoIn(nome="Pessoa", cargo="Gerente"))
    interacao = service.registrar_interacao(session, cliente.id, _interacao(contato_id=contato.id))
    service.remover_contato(session, contato.id)
    session.refresh(interacao)
    assert interacao.contato_id is None
    assert service.listar_contatos(session, cliente.id) == []
    assert _eventos(session, cliente.id) == [
        "Cliente criado",
        "Contato adicionado",
        "Contato atualizado: cargo",
        "Contato removido",
    ]


def test_interaction_contact_must_belong_to_client(session: Session) -> None:
    a, b = _cliente(session, "A"), _cliente(session, "B")
    contato_b = service.adicionar_contato(session, b.id, ContatoIn(nome="Pessoa"))
    with pytest.raises(service.NaoEncontrado):
        service.registrar_interacao(session, a.id, _interacao(contato_id=contato_b.id))


def test_timeline_is_newest_first_and_limited(session: Session) -> None:
    cliente = _cliente(session)
    for dia in (3, 1, 2):
        service.registrar_interacao(
            session,
            cliente.id,
            _interacao(f"dia {dia}", ocorrida_em=datetime(2026, 9, dia, tzinfo=UTC)),
        )
    linha = service.listar_interacoes(session, cliente.id, por_pagina=3)
    assert [i.resumo for i in linha.itens] == ["Cliente criado", "dia 3", "dia 2"]


def test_interactions_have_no_edit_or_delete_operation() -> None:
    """D5: o histórico só aceita acréscimo; o serviço não oferece edição nem exclusão."""
    proibidos = ("atualiz", "edit", "remov", "exclu", "apag")
    nomes = [n for n in dir(service) if "interac" in n and any(p in n for p in proibidos)]
    assert nomes == []


def test_list_sorts_names_ignoring_accents_and_case(session: Session) -> None:
    for nome in ("Zeta", "ágil", "Beta", "Ômega"):
        _cliente(session, nome)
    assert [c.nome for c in service.listar_clientes(session).itens] == [
        "ágil",
        "Beta",
        "Ômega",
        "Zeta",
    ]
