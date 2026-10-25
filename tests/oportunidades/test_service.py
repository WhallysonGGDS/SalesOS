"""Regras do funil (R1 a R6, R9 e histórico imutável) com dados fictícios."""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salesos.features.clientes import service as clientes
from salesos.features.clientes.models import Cliente, Interacao
from salesos.features.clientes.schemas import ClienteIn
from salesos.features.oportunidades import service
from salesos.features.oportunidades.models import ETAPAS_ABERTAS, Movimentacao, Oportunidade
from salesos.features.oportunidades.schemas import MudancaEtapaIn, OportunidadeIn


def _cliente(session: Session) -> Cliente:
    return clientes.criar_cliente(
        session, ClienteIn(tipo="PJ", nome="Empresa Ficticia", origem="site")
    )


def _nova(session: Session, valor: int | None = 150000, **extra: Any) -> Oportunidade:
    dados = OportunidadeIn(titulo="Projeto ficticio", valor_centavos=valor, **extra)
    return service.criar_oportunidade(session, _cliente(session).id, dados)


def _mudar(session: Session, oportunidade: Oportunidade, etapa: str, **extra: str) -> Oportunidade:
    return service.mudar_etapa(session, oportunidade.id, MudancaEtapaIn(etapa=etapa, **extra))


def _historico(session: Session, oportunidade: Oportunidade) -> list[tuple[Any, ...]]:
    linhas = session.execute(
        select(
            Movimentacao.id,
            Movimentacao.de_etapa,
            Movimentacao.para_etapa,
            Movimentacao.ocorrida_em,
        )
        .where(Movimentacao.oportunidade_id == oportunidade.id)
        .order_by(Movimentacao.id)
    )
    return [tuple(linha) for linha in linhas]


def _eventos(session: Session, cliente_id: int) -> list[str]:
    query = (
        select(Interacao.resumo)
        .where(Interacao.cliente_id == cliente_id, Interacao.tipo == "sistema")
        .order_by(Interacao.id)
    )
    return [e for e in session.scalars(query) if e.startswith("Oportunidade")]


def _contagens(session: Session) -> tuple[int, int, int]:
    return (
        session.scalar(select(func.count()).select_from(Oportunidade)) or 0,
        session.scalar(select(func.count()).select_from(Movimentacao)) or 0,
        session.scalar(select(func.count()).select_from(Interacao)) or 0,
    )


def test_creation_starts_in_new_lead_with_initial_movement_and_event(session: Session) -> None:
    oportunidade = _nova(session)
    assert (oportunidade.etapa, oportunidade.fechada_em) == ("novo_lead", None)
    historico = _historico(session, oportunidade)
    assert [(de, para) for _i, de, para, _q in historico] == [(None, "novo_lead")]
    assert _eventos(session, oportunidade.cliente_id) == [f"Oportunidade #{oportunidade.id} criada"]


def test_creation_for_missing_client_is_not_found(session: Session) -> None:
    with pytest.raises(clientes.NaoEncontrado):
        service.criar_oportunidade(session, 999, OportunidadeIn(titulo="X"))


def test_free_movement_between_open_stages(session: Session) -> None:
    oportunidade = _nova(session)
    caminho = ["negociacao", "qualificacao", "proposta_enviada", "novo_lead", "negociacao"]
    for etapa in caminho:
        _mudar(session, oportunidade, etapa)
    pares = [(de, para) for _i, de, para, _q in _historico(session, oportunidade)]
    assert pares == list(
        zip([None, "novo_lead", *caminho[:-1]], ["novo_lead", *caminho], strict=True)
    )
    assert _eventos(session, oportunidade.cliente_id)[-1] == (
        f"Oportunidade #{oportunidade.id} movida para Negociação"
    )


def test_same_stage_creates_nothing(session: Session) -> None:
    oportunidade = _nova(session)
    _mudar(session, oportunidade, "qualificacao")
    antes = _contagens(session)
    _mudar(session, oportunidade, "qualificacao")
    _mudar(session, oportunidade, "qualificacao")
    assert _contagens(session) == antes


def test_win_sets_closing_date_and_requires_positive_value(session: Session) -> None:
    for valor in (None, 0):
        oportunidade = _nova(session, valor=valor)
        antes = _contagens(session)
        with pytest.raises(service.RegraViolada) as erro:
            _mudar(session, oportunidade, "ganha")
        assert erro.value.campo == "etapa"
        session.rollback()
        assert _contagens(session) == antes
        assert session.get(Oportunidade, oportunidade.id).etapa == "novo_lead"  # type: ignore[union-attr]
    ganha = _mudar(session, _nova(session, valor=1), "ganha")
    assert ganha.fechada_em is not None


def test_won_opportunity_cannot_lose_its_value_on_edit(session: Session) -> None:
    oportunidade = _mudar(session, _nova(session), "ganha")
    for valor in (None, 0):
        with pytest.raises(service.RegraViolada) as erro:
            service.atualizar_oportunidade(
                session,
                oportunidade.id,
                OportunidadeIn(titulo="Projeto ficticio", valor_centavos=valor),
            )
        assert erro.value.campo == "valor_centavos"
        session.rollback()


def test_loss_records_reason_and_detail(session: Session) -> None:
    oportunidade = _mudar(
        session, _nova(session), "perdida", motivo_perda="preco", motivo_detalhe="Caro"
    )
    assert (oportunidade.motivo_perda, oportunidade.motivo_detalhe) == ("preco", "Caro")
    assert oportunidade.fechada_em is not None


@pytest.mark.parametrize(("final", "outro"), [("ganha", "perdida"), ("perdida", "ganha")])
def test_final_to_final_requires_reopening_first(session: Session, final: str, outro: str) -> None:
    extra = {"motivo_perda": "preco"}
    oportunidade = _mudar(session, _nova(session), final, **(extra if final == "perdida" else {}))
    antes = _contagens(session)
    with pytest.raises(service.RegraViolada, match="Reabra"):
        _mudar(session, oportunidade, outro, **(extra if outro == "perdida" else {}))
    session.rollback()
    assert _contagens(session) == antes
    _mudar(session, oportunidade, "negociacao")
    _mudar(session, oportunidade, outro, **(extra if outro == "perdida" else {}))
    assert session.get(Oportunidade, oportunidade.id).etapa == outro  # type: ignore[union-attr]


@pytest.mark.parametrize("destino", ETAPAS_ABERTAS)
def test_reopening_clears_closing_fields_and_keeps_history(session: Session, destino: str) -> None:
    oportunidade = _mudar(
        session, _nova(session), "perdida", motivo_perda="concorrente", motivo_detalhe="Outro"
    )
    historico = _historico(session, oportunidade)
    eventos = _eventos(session, oportunidade.cliente_id)
    reaberta = _mudar(session, oportunidade, destino)
    assert (
        reaberta.etapa,
        reaberta.fechada_em,
        reaberta.motivo_perda,
        reaberta.motivo_detalhe,
    ) == (
        destino,
        None,
        None,
        None,
    )
    depois = _historico(session, oportunidade)
    assert depois[: len(historico)] == historico
    assert [(de, para) for _i, de, para, _q in depois[len(historico) :]] == [("perdida", destino)]
    assert _eventos(session, oportunidade.cliente_id)[: len(eventos)] == eventos
    assert _eventos(session, oportunidade.cliente_id)[-1].startswith(
        f"Oportunidade #{oportunidade.id} reaberta em "
    )


def test_edit_records_only_changed_field_names(session: Session) -> None:
    oportunidade = _nova(session)
    dados = OportunidadeIn(
        titulo="Outro titulo ficticio", valor_centavos=150000, observacoes="Nota"
    )
    service.atualizar_oportunidade(session, oportunidade.id, dados)
    service.atualizar_oportunidade(session, oportunidade.id, dados)  # sem mudança: sem evento
    assert _eventos(session, oportunidade.cliente_id)[1:] == [
        f"Oportunidade #{oportunidade.id} atualizada: observacoes, titulo"
    ]


def test_archived_client_accepts_and_anonymized_refuses(session: Session) -> None:
    oportunidade = _nova(session)
    clientes.arquivar_cliente(session, oportunidade.cliente_id)
    _mudar(session, oportunidade, "qualificacao")
    service.atualizar_oportunidade(session, oportunidade.id, OportunidadeIn(titulo="Novo titulo"))
    service.criar_oportunidade(session, oportunidade.cliente_id, OportunidadeIn(titulo="Outra"))
    clientes.anonimizar_cliente(session, oportunidade.cliente_id)
    with pytest.raises(clientes.Bloqueado):
        service.criar_oportunidade(session, oportunidade.cliente_id, OportunidadeIn(titulo="X"))
    with pytest.raises(clientes.Bloqueado):
        _mudar(session, oportunidade, "negociacao")
    with pytest.raises(clientes.Bloqueado):
        service.atualizar_oportunidade(session, oportunidade.id, OportunidadeIn(titulo="X"))


def test_event_failure_rolls_back_the_whole_operation(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    oportunidade = _nova(session)
    antes = _contagens(session)

    def falhar(*_a: Any) -> None:
        raise RuntimeError("falha injetada")

    monkeypatch.setattr(service, "registrar_evento", falhar)
    operacoes: list[Callable[[], object]] = [
        lambda: _mudar(session, oportunidade, "negociacao"),
        lambda: service.criar_oportunidade(
            session, oportunidade.cliente_id, OportunidadeIn(titulo="X")
        ),
    ]
    for operacao in operacoes:
        with pytest.raises(RuntimeError):
            operacao()
        session.rollback()
        assert _contagens(session) == antes
    assert session.get(Oportunidade, oportunidade.id).etapa == "novo_lead"  # type: ignore[union-attr]


def test_history_is_never_rewritten_by_any_operation(session: Session) -> None:
    oportunidade = _nova(session)
    vistos: list[tuple[Any, ...]] = []
    passos: list[Callable[[], object]] = [
        lambda: _mudar(session, oportunidade, "qualificacao"),
        lambda: _mudar(session, oportunidade, "perdida", motivo_perda="adiado"),
        lambda: _mudar(session, oportunidade, "proposta_enviada"),
        lambda: _mudar(session, oportunidade, "ganha"),
        lambda: service.atualizar_oportunidade(
            session, oportunidade.id, OportunidadeIn(titulo="Novo", valor_centavos=5)
        ),
        lambda: clientes.anonimizar_cliente(session, oportunidade.cliente_id),
    ]
    for passo in passos:
        vistos = _historico(session, oportunidade)
        passo()
        session.expire_all()
        assert _historico(session, oportunidade)[: len(vistos)] == vistos
    assert len(_historico(session, oportunidade)) == 5
    publicas = {n for n in dir(service) if not n.startswith("_")}
    assert not {n for n in publicas if "movimenta" in n} - {"movimentacoes"}


def test_changing_only_the_reason_of_a_lost_opportunity_asks_to_reopen(session: Session) -> None:
    oportunidade = _mudar(session, _nova(session), "perdida", motivo_perda="preco")
    antes = _contagens(session)
    _mudar(session, oportunidade, "perdida", motivo_perda="preco")  # sem mudança: nada (R5)
    with pytest.raises(service.RegraViolada, match="reabra") as erro:
        _mudar(session, oportunidade, "perdida", motivo_perda="adiado")
    assert erro.value.campo == "motivo_perda"
    session.rollback()
    assert _contagens(session) == antes
    assert session.get(Oportunidade, oportunidade.id).motivo_perda == "preco"  # type: ignore[union-attr]
