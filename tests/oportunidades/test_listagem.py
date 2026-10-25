"""Funil, lista paginada e filtros de período (R7) com datas controladas (dados fictícios)."""

from datetime import date, datetime

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.clientes.schemas import ClienteIn
from salesos.features.oportunidades import service
from salesos.features.oportunidades.models import ETAPAS, Oportunidade
from salesos.features.oportunidades.schemas import FiltroFunil, MudancaEtapaIn, OportunidadeIn


def _cliente_id(session: Session) -> int:
    dados = ClienteIn(tipo="PJ", nome="Empresa Ficticia", origem="site")
    return clientes.criar_cliente(session, dados).id


def _nova(session: Session, cliente_id: int, titulo: str, criada: datetime) -> Oportunidade:
    oportunidade = service.criar_oportunidade(
        session, cliente_id, OportunidadeIn(titulo=titulo, valor_centavos=100)
    )
    session.execute(  # created_at vem do banco; o teste fixa o momento (UTC, sem fuso)
        update(Oportunidade).where(Oportunidade.id == oportunidade.id).values(created_at=criada)
    )
    session.commit()
    return oportunidade


def _fechar(session: Session, oportunidade: Oportunidade, etapa: str, quando: datetime) -> None:
    extra = {"motivo_perda": "preco"} if etapa == "perdida" else {}
    service.mudar_etapa(session, oportunidade.id, MudancaEtapaIn(etapa=etapa, **extra))
    session.execute(
        update(Oportunidade).where(Oportunidade.id == oportunidade.id).values(fechada_em=quando)
    )
    session.commit()


def _titulos(itens: list[Oportunidade]) -> set[str]:
    return {o.titulo for o in itens}


@pytest.mark.usefixtures("fuso")
def test_period_uses_opening_for_open_and_closing_for_closed(session: Session) -> None:
    cliente_id = _cliente_id(session)
    # 2026-10-01 03:00 UTC = meia-noite local (-03:00); 02:59:59 ainda é 30/09 local.
    _nova(session, cliente_id, "aberta-no-dia", datetime(2026, 10, 1, 3, 0, 0))
    _nova(session, cliente_id, "aberta-na-vespera", datetime(2026, 10, 1, 2, 59, 59))
    # Aberta antes do período, fechada dentro dele: entra pela data de fechamento.
    ganha = _nova(session, cliente_id, "ganha-23h30-local", datetime(2026, 9, 1, 12))
    _fechar(session, ganha, "ganha", datetime(2026, 10, 2, 2, 30))  # 01/10 23:30 local
    perdida = _nova(session, cliente_id, "perdida-fora", datetime(2026, 10, 1, 12))
    _fechar(session, perdida, "perdida", datetime(2026, 10, 2, 3, 0))  # 02/10 00:00 local

    filtro = FiltroFunil(de=date(2026, 10, 1), ate=date(2026, 10, 1))
    pagina = service.listar_oportunidades(session, filtro)
    assert _titulos(pagina.itens) == {"aberta-no-dia", "ganha-23h30-local"}
    so_de = service.listar_oportunidades(session, FiltroFunil(de=date(2026, 10, 2)))
    assert _titulos(so_de.itens) == {"perdida-fora"}
    so_ate = service.listar_oportunidades(session, FiltroFunil(ate=date(2026, 9, 30)))
    assert _titulos(so_ate.itens) == {"aberta-na-vespera"}


def test_situation_filter_and_stage_filter(session: Session) -> None:
    cliente_id = _cliente_id(session)
    aberta = _nova(session, cliente_id, "aberta", datetime(2026, 10, 1, 12))
    ganha = _nova(session, cliente_id, "ganha", datetime(2026, 10, 1, 12))
    perdida = _nova(session, cliente_id, "perdida", datetime(2026, 10, 1, 12))
    _fechar(session, ganha, "ganha", datetime(2026, 10, 3, 12))
    _fechar(session, perdida, "perdida", datetime(2026, 10, 3, 12))

    def titulos(situacao: str, etapa: str | None = None) -> set[str]:
        filtro = FiltroFunil.model_validate({"situacao": situacao})
        return _titulos(service.listar_oportunidades(session, filtro, etapa=etapa).itens)

    assert titulos("todas") == {"aberta", "ganha", "perdida"}
    assert titulos("abertas") == {"aberta"}
    assert titulos("ganhas") == {"ganha"}
    assert titulos("perdidas") == {"perdida"}
    assert titulos("todas", etapa="novo_lead") == {"aberta"}
    assert titulos("abertas", etapa="ganha") == set()  # etapa fora da situação: nada
    assert aberta.etapa == "novo_lead"
    funil = service.listar_funil(session, FiltroFunil(situacao="abertas"))
    assert list(funil) == ["novo_lead", "qualificacao", "proposta_enviada", "negociacao"]
    assert list(service.listar_funil(session, FiltroFunil())) == list(ETAPAS)


def test_listings_are_limited(session: Session) -> None:
    cliente_id = _cliente_id(session)
    for i in range(25):
        _nova(session, cliente_id, f"op-{i:02d}", datetime(2026, 10, 1, 12, i))
    coluna = service.listar_funil(session, FiltroFunil())["novo_lead"]
    assert len(coluna) == service.POR_COLUNA == 20
    assert coluna[0].titulo == "op-24"  # mais recentes primeiro
    primeira = service.listar_oportunidades(session, FiltroFunil(), pagina=1)
    segunda = service.listar_oportunidades(session, FiltroFunil(), pagina=2)
    assert (len(primeira.itens), primeira.tem_proxima) == (20, True)
    assert (len(segunda.itens), segunda.tem_proxima) == (5, False)
    assert len(service.oportunidades_do_cliente(session, cliente_id)) == 25
    assert service.DO_CLIENTE_MAX == 50
