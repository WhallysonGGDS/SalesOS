"""Rotas e telas do funil (Fase 03, ADR 0006).

Rotas finas: validam a entrada, chamam o serviço e respondem 303 depois de cada POST
bem-sucedido. Só `/etapa` e a criação gravam movimentações; nenhuma rota as edita ou apaga.
"""

from datetime import date
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from salesos.db import get_session
from salesos.dinheiro import reais
from salesos.features.clientes import service as clientes
from salesos.features.oportunidades import service
from salesos.features.oportunidades.models import ETAPAS, ETAPAS_ABERTAS, MOTIVOS_PERDA
from salesos.features.oportunidades.schemas import FiltroFunil, MudancaEtapaIn, OportunidadeIn
from salesos.features.tarefas import service as tarefas
from salesos.formularios import IdDep, RegraViolada, formulario, renderizar, validar, ver

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]

CAMPOS_OPORTUNIDADE = ("titulo", "valor_centavos", "previsao_fechamento", "observacoes")
CAMPOS_ETAPA = ("etapa", "motivo_perda", "motivo_detalhe")
ROTULOS_MOTIVOS = {
    "preco": "Preço",
    "concorrente": "Escolheu um concorrente",
    "sem_orcamento": "Sem orçamento",
    "sem_resposta": "Parou de responder",
    "adiado": "Projeto adiado",
    "outro": "Outro motivo",
}
SITUACOES = {"todas": "Todas", "abertas": "Abertas", "ganhas": "Ganhas", "perdidas": "Perdidas"}


def _pagina(request: Request, nome: str, contexto: dict[str, Any], status: int = 200) -> Response:
    base = {
        "secao": "funil",
        "etapas": ETAPAS,
        "etapas_abertas": ETAPAS_ABERTAS,
        "motivos": MOTIVOS_PERDA,
        "rotulos": tarefas.ROTULOS_TAREFAS | service.ROTULOS_ETAPAS | ROTULOS_MOTIVOS | SITUACOES,
        "situacoes": SITUACOES,
    }
    return renderizar(request, nome, base | contexto, status)


def _filtro(request: Request) -> tuple[dict[str, str], FiltroFunil | dict[str, str]]:
    brutos = {c: v for c in ("situacao", "de", "ate") if (v := request.query_params.get(c))}
    return brutos, validar(FiltroFunil, brutos)


def _data_curta(valor: date | None) -> str:
    return "" if valor is None else valor.strftime("%d/%m/%Y")


def _valor(centavos: int | None) -> str:
    return "" if centavos is None else reais(centavos)


# --- funil e lista ---


@router.get("/oportunidades", response_class=HTMLResponse)
def funil(request: Request, session: SessionDep) -> Response:
    brutos, filtro = _filtro(request)
    if not isinstance(filtro, FiltroFunil):
        contexto: dict[str, Any] = {"filtros": brutos, "erros": filtro, "colunas": {}, "nomes": {}}
        return _pagina(request, "oportunidades/funil.html", contexto, 422)
    colunas = service.listar_funil(session, filtro)
    todas = [o for coluna in colunas.values() for o in coluna]
    contexto = {
        "filtros": brutos,
        "erros": {},
        "colunas": colunas,
        "nomes": service.nomes_clientes(session, (o.cliente_id for o in todas)),
        "por_coluna": service.POR_COLUNA,
    }
    return _pagina(request, "oportunidades/funil.html", contexto)


@router.get("/oportunidades/lista", response_class=HTMLResponse)
def lista(
    request: Request,
    session: SessionDep,
    etapa: Annotated[str | None, Query(pattern="^(" + "|".join(ETAPAS) + ")$")] = None,
    pagina: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> Response:
    brutos, filtro = _filtro(request)
    if etapa:
        brutos["etapa"] = etapa
    if not isinstance(filtro, FiltroFunil):
        contexto: dict[str, Any] = {
            "filtros": brutos,
            "erros": filtro,
            "resultado": None,
            "nomes": {},
        }
        return _pagina(request, "oportunidades/lista.html", contexto, 422)
    resultado = service.listar_oportunidades(session, filtro, etapa, pagina)

    def link(numero: int) -> str:
        return "/oportunidades/lista?" + urlencode(brutos | {"pagina": numero})

    contexto = {
        "filtros": brutos,
        "erros": {},
        "resultado": resultado,
        "nomes": service.nomes_clientes(session, (o.cliente_id for o in resultado.itens)),
        "anterior": link(pagina - 1) if pagina > 1 else None,
        "proxima": link(pagina + 1) if resultado.tem_proxima else None,
    }
    return _pagina(request, "oportunidades/lista.html", contexto)


# --- criar e editar ---


def _cliente_do_formulario(valor: str | None) -> int:
    if valor is None or not valor.isascii() or not valor.isdigit() or len(valor) > 12:
        raise clientes.NaoEncontrado("cliente não encontrado")
    return int(valor)


@router.get("/oportunidades/nova", response_class=HTMLResponse)
def nova(
    request: Request, session: SessionDep, cliente_id: Annotated[str | None, Query()] = None
) -> Response:
    cliente = clientes.cliente_editavel(session, _cliente_do_formulario(cliente_id))
    contexto: dict[str, Any] = {"oportunidade": None, "cliente": cliente, "dados": {}, "erros": {}}
    return _pagina(request, "oportunidades/form.html", contexto)


@router.post("/oportunidades")
async def criar(request: Request, session: SessionDep) -> Response:
    dados = await formulario(request, (*CAMPOS_OPORTUNIDADE, "cliente_id"))
    cliente = clientes.cliente_editavel(
        session, _cliente_do_formulario(dados.pop("cliente_id", None))
    )
    entrada = validar(OportunidadeIn, dados)
    if isinstance(entrada, OportunidadeIn):
        return ver(f"/oportunidades/{service.criar_oportunidade(session, cliente.id, entrada).id}")
    contexto: dict[str, Any] = {
        "oportunidade": None,
        "cliente": cliente,
        "dados": dados,
        "erros": entrada,
    }
    return _pagina(request, "oportunidades/form.html", contexto, 422)


def _dados_atuais(oportunidade: Any) -> dict[str, str]:
    return {
        "titulo": oportunidade.titulo,
        "valor_centavos": _valor(oportunidade.valor_centavos).removeprefix("R$ "),
        "previsao_fechamento": str(oportunidade.previsao_fechamento or ""),
        "observacoes": oportunidade.observacoes or "",
    }


@router.get("/oportunidades/{oportunidade_id}/editar", response_class=HTMLResponse)
def editar(request: Request, session: SessionDep, oportunidade_id: IdDep) -> Response:
    oportunidade = service.oportunidade_editavel(session, oportunidade_id)
    contexto: dict[str, Any] = {
        "oportunidade": oportunidade,
        "cliente": clientes.obter_cliente(session, oportunidade.cliente_id),
        "dados": _dados_atuais(oportunidade),
        "erros": {},
    }
    return _pagina(request, "oportunidades/form.html", contexto)


@router.post("/oportunidades/{oportunidade_id}")
async def atualizar(request: Request, session: SessionDep, oportunidade_id: IdDep) -> Response:
    oportunidade = service.oportunidade_editavel(session, oportunidade_id)
    dados = await formulario(request, CAMPOS_OPORTUNIDADE)
    entrada = validar(OportunidadeIn, dados)
    try:
        if isinstance(entrada, OportunidadeIn):
            service.atualizar_oportunidade(session, oportunidade_id, entrada)
            return ver(f"/oportunidades/{oportunidade_id}")
    except RegraViolada as erro:
        session.rollback()
        entrada = {erro.campo: str(erro)}
    contexto: dict[str, Any] = {
        "oportunidade": oportunidade,
        "cliente": clientes.obter_cliente(session, oportunidade.cliente_id),
        "dados": dados,
        "erros": entrada,
    }
    return _pagina(request, "oportunidades/form.html", contexto, 422)


# --- detalhe e etapa ---


def _detalhe(
    request: Request, session: Session, oportunidade_id: int, status: int = 200, **extra: Any
) -> Response:
    oportunidade = service.obter_oportunidade(session, oportunidade_id)
    cliente = clientes.obter_cliente(session, oportunidade.cliente_id)
    contexto: dict[str, Any] = {
        "oportunidade": oportunidade,
        "cliente": cliente,
        "historico": service.movimentacoes(session, oportunidade_id),
        "tarefas": tarefas.tarefas_da_oportunidade(session, oportunidade_id),
        "tarefas_max": tarefas.RELACIONADAS_MAX,
        "mudanca": {
            "etapa": oportunidade.etapa,
            "motivo_perda": oportunidade.motivo_perda,
            "motivo_detalhe": oportunidade.motivo_detalhe,
        },
        "erros": {},
    }
    return _pagina(request, "oportunidades/detalhe.html", contexto | extra, status)


@router.get("/oportunidades/{oportunidade_id}", response_class=HTMLResponse)
def detalhe(request: Request, session: SessionDep, oportunidade_id: IdDep) -> Response:
    return _detalhe(request, session, oportunidade_id)


@router.post("/oportunidades/{oportunidade_id}/etapa")
async def mudar_etapa(request: Request, session: SessionDep, oportunidade_id: IdDep) -> Response:
    service.oportunidade_editavel(session, oportunidade_id)
    dados = await formulario(request, CAMPOS_ETAPA)
    entrada = validar(MudancaEtapaIn, dados)
    try:
        if isinstance(entrada, MudancaEtapaIn):
            service.mudar_etapa(session, oportunidade_id, entrada)
            return ver(f"/oportunidades/{oportunidade_id}")
    except RegraViolada as erro:
        session.rollback()
        entrada = {erro.campo: str(erro)}
    return _detalhe(request, session, oportunidade_id, 422, mudanca=dados, erros=entrada)


def configurar(app: FastAPI) -> None:
    app.include_router(router)
    app.state.templates.env.filters["reais"] = _valor
    app.state.templates.env.filters["data_curta"] = _data_curta
