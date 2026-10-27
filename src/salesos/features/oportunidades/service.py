"""Regras do funil (Fase 03, ADR 0006).

Cada função é uma unidade de trabalho: a operação, a movimentação e o evento do cliente vão no
mesmo commit (R9). Eventos levam só o número da oportunidade, a ação e nomes de campos ou de
etapas, nunca título, observações, motivo detalhado ou valor. Não existe função que edite ou
apague movimentações.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from salesos.features.clientes.models import Cliente
from salesos.features.clientes.service import (
    NaoEncontrado,
    cliente_editavel,
    registrar_evento,
)
from salesos.features.oportunidades.models import (
    ETAPAS,
    ETAPAS_ABERTAS,
    ETAPAS_FINAIS,
    Movimentacao,
    Oportunidade,
)
from salesos.features.oportunidades.schemas import FiltroFunil, MudancaEtapaIn, OportunidadeIn
from salesos.formularios import RegraViolada
from salesos.periodo import intervalo_utc

POR_COLUNA = 20
POR_PAGINA = 20
DO_CLIENTE_MAX = 50
MOVIMENTACOES_MAX = 200
ROTULOS_ETAPAS = {
    "novo_lead": "Novo lead",
    "qualificacao": "Qualificação",
    "proposta_enviada": "Proposta enviada",
    "negociacao": "Negociação",
    "ganha": "Venda ganha",
    "perdida": "Venda perdida",
}
SITUACOES = {
    "todas": ETAPAS,
    "abertas": ETAPAS_ABERTAS,
    "ganhas": ("ganha",),
    "perdidas": ("perdida",),
}


@dataclass(frozen=True)
class PaginaOportunidades:
    itens: list[Oportunidade]
    pagina: int
    tem_proxima: bool


def _agora() -> datetime:
    return datetime.now(UTC)


def _movimentar(session: Session, oportunidade: Oportunidade, de: str | None, para: str) -> None:
    session.add(
        Movimentacao(
            oportunidade_id=oportunidade.id, de_etapa=de, para_etapa=para, ocorrida_em=_agora()
        )
    )


def obter_oportunidade(session: Session, oportunidade_id: int) -> Oportunidade:
    oportunidade = session.get(Oportunidade, oportunidade_id)
    if oportunidade is None:
        raise NaoEncontrado("oportunidade não encontrada")
    return oportunidade


def oportunidade_editavel(session: Session, oportunidade_id: int) -> Oportunidade:
    oportunidade = obter_oportunidade(session, oportunidade_id)
    cliente_editavel(session, oportunidade.cliente_id)  # R6: anonimizado → Bloqueado
    return oportunidade


def criar_oportunidade(session: Session, cliente_id: int, dados: OportunidadeIn) -> Oportunidade:
    cliente = cliente_editavel(session, cliente_id)
    oportunidade = Oportunidade(cliente_id=cliente.id, etapa="novo_lead", **dados.model_dump())
    session.add(oportunidade)
    session.flush()
    _movimentar(session, oportunidade, None, "novo_lead")
    registrar_evento(session, cliente.id, f"Oportunidade #{oportunidade.id} criada")
    session.commit()
    return oportunidade


def atualizar_oportunidade(
    session: Session, oportunidade_id: int, dados: OportunidadeIn
) -> Oportunidade:
    oportunidade = oportunidade_editavel(session, oportunidade_id)
    if oportunidade.etapa == "ganha" and not dados.valor_centavos:
        raise RegraViolada("valor_centavos", "Venda ganha precisa de valor maior que zero")
    mudou = []
    for campo, valor in dados.model_dump().items():
        if getattr(oportunidade, campo) != valor:
            setattr(oportunidade, campo, valor)
            mudou.append(campo)
    if mudou:
        resumo = f"Oportunidade #{oportunidade.id} atualizada: {', '.join(sorted(mudou))}"
        registrar_evento(session, oportunidade.cliente_id, resumo)
        session.commit()
    return oportunidade


def mudar_etapa(session: Session, oportunidade_id: int, dados: MudancaEtapaIn) -> Oportunidade:
    oportunidade = oportunidade_editavel(session, oportunidade_id)
    de, para = oportunidade.etapa, dados.etapa
    if de == para:
        motivo = (oportunidade.motivo_perda, oportunidade.motivo_detalhe)
        if (dados.motivo_perda, dados.motivo_detalhe) != motivo:
            raise RegraViolada(
                "motivo_perda",
                "Para corrigir o motivo, reabra em uma etapa aberta e marque como perdida de novo",
            )
        return oportunidade  # R5: envio repetido não gera movimentação nem evento
    if de in ETAPAS_FINAIS and para in ETAPAS_FINAIS:
        raise RegraViolada("etapa", "Reabra em uma etapa aberta antes de mudar o resultado")
    if para == "ganha" and not oportunidade.valor_centavos:
        raise RegraViolada("etapa", "Informe um valor maior que zero antes de marcar como ganha")
    oportunidade.etapa = para
    oportunidade.fechada_em = _agora() if para in ETAPAS_FINAIS else None
    oportunidade.motivo_perda = dados.motivo_perda
    oportunidade.motivo_detalhe = dados.motivo_detalhe
    _movimentar(session, oportunidade, de, para)
    acao = "reaberta em" if de in ETAPAS_FINAIS else "movida para"
    resumo = f"Oportunidade #{oportunidade.id} {acao} {ROTULOS_ETAPAS[para]}"
    registrar_evento(session, oportunidade.cliente_id, resumo)
    session.commit()
    return oportunidade


def _filtrada(filtro: FiltroFunil, etapas: tuple[str, ...]) -> Select[Oportunidade]:
    query = select(Oportunidade).where(Oportunidade.etapa.in_(etapas))
    inicio, fim = intervalo_utc(filtro.de, filtro.ate)
    # R7: abertas pela abertura, fechadas pelo fechamento. `datetime()` normaliza o texto do
    # SQLite (CURRENT_TIMESTAMP não tem frações; o SQLAlchemy grava microssegundos).
    referencia = func.datetime(func.coalesce(Oportunidade.fechada_em, Oportunidade.created_at))
    if inicio is not None:
        query = query.where(referencia >= inicio.strftime("%Y-%m-%d %H:%M:%S"))
    if fim is not None:
        query = query.where(referencia < fim.strftime("%Y-%m-%d %H:%M:%S"))
    return query.order_by(Oportunidade.created_at.desc(), Oportunidade.id.desc())


def listar_funil(session: Session, filtro: FiltroFunil) -> dict[str, list[Oportunidade]]:
    return {
        etapa: list(session.scalars(_filtrada(filtro, (etapa,)).limit(POR_COLUNA)))
        for etapa in SITUACOES[filtro.situacao]
    }


def listar_oportunidades(
    session: Session, filtro: FiltroFunil, etapa: str | None = None, pagina: int = 1
) -> PaginaOportunidades:
    etapas = SITUACOES[filtro.situacao]
    if etapa is not None:
        etapas = tuple(e for e in etapas if e == etapa)
    pagina = max(1, pagina)
    query = _filtrada(filtro, etapas).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA + 1)
    itens = list(session.scalars(query))
    return PaginaOportunidades(itens[:POR_PAGINA], pagina, len(itens) > POR_PAGINA)


def oportunidades_do_cliente(session: Session, cliente_id: int) -> list[Oportunidade]:
    query = (
        select(Oportunidade)
        .where(Oportunidade.cliente_id == cliente_id)
        .order_by(Oportunidade.created_at.desc(), Oportunidade.id.desc())
        .limit(DO_CLIENTE_MAX)
    )
    return list(session.scalars(query))


def movimentacoes(session: Session, oportunidade_id: int) -> list[Movimentacao]:
    query = (
        select(Movimentacao)
        .where(Movimentacao.oportunidade_id == oportunidade_id)
        .order_by(Movimentacao.ocorrida_em, Movimentacao.id)
        .limit(MOVIMENTACOES_MAX)
    )
    return list(session.scalars(query))


def nomes_clientes(session: Session, oportunidades: list[Oportunidade]) -> dict[int, str]:
    """Nomes dos clientes de uma tela (uma consulta, limitada pelas próprias listagens)."""
    ids = {o.cliente_id for o in oportunidades}
    query = select(Cliente.id, Cliente.nome).where(Cliente.id.in_(ids))
    return {cliente_id: nome for cliente_id, nome in session.execute(query)}
