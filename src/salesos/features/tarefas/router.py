"""Rotas e telas das tarefas (Fase 04, ADR 0007).

Rotas finas: validam a entrada, chamam o serviço e respondem 303 depois de cada POST
bem-sucedido. Nenhuma rota edita ou apaga o histórico; não há exclusão de tarefa (D8).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from salesos.db import get_session
from salesos.features.clientes import service as clientes
from salesos.features.oportunidades import service as oportunidades
from salesos.features.oportunidades.models import Oportunidade
from salesos.features.tarefas import service
from salesos.features.tarefas.models import ESTADOS, PRIORIDADES, TIPOS_TAREFA, Tarefa
from salesos.features.tarefas.schemas import FiltroTarefas, TarefaIn
from salesos.formularios import (
    IdDep,
    RegraViolada,
    formulario,
    hora_local,
    renderizar,
    validar,
    ver,
)

logger = logging.getLogger(__name__)
router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]

CAMPOS_TAREFA = ("tipo", "titulo", "descricao", "prioridade", "prazo", "oportunidade_id")
CAMPOS_FILTRO = ("estado", "prioridade", "tipo", "de", "ate")
ROTULOS = {
    "ligacao": "Ligação",
    "reuniao": "Reunião",
    "mensagem": "Mensagem",
    "retorno": "Retorno comercial",
    "baixa": "Baixa",
    "normal": "Normal",
    "alta": "Alta",
    "pendente": "Pendente",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
    "todas": "Todas",
    "criada": "Criada",
    "reaberta": "Reaberta",
}


def _pagina(request: Request, nome: str, contexto: dict[str, Any], status: int = 200) -> Response:
    base = {
        "secao": "tarefas",
        "tipos": TIPOS_TAREFA,
        "prioridades": PRIORIDADES,
        "estados": (*ESTADOS, "todas"),
        "rotulos": ROTULOS,
    }
    return renderizar(request, nome, base | contexto, status)


def _id(valor: str | None) -> int:
    """Id vindo de formulário ou da URL de consulta; fora do inteiro de 64 bits → não encontrado."""
    if valor is None or not valor.isascii() or not valor.isdigit() or len(valor) > 18:
        raise clientes.NaoEncontrado("não encontrado")
    return int(valor)


def _entrada(dados: dict[str, str]) -> TarefaIn | dict[str, str]:
    bruto: dict[str, Any] = dict(dados)
    if dados.get("prazo"):
        bruto["prazo"] = hora_local(dados["prazo"])
    if not dados.get("oportunidade_id"):
        bruto.pop("oportunidade_id", None)  # "Nenhuma" no formulário
    return validar(TarefaIn, bruto)


def _prazo_no_formulario(prazo: datetime) -> str:
    """Valor do `datetime-local`: o prazo em UTC aparece no fuso deste computador."""
    return prazo.replace(tzinfo=UTC).astimezone().strftime("%Y-%m-%dT%H:%M")


# --- agenda (D9: lista ordenada, sem grade) ---


@router.get("/tarefas", response_class=HTMLResponse)
def agenda(
    request: Request,
    session: SessionDep,
    pagina: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> Response:
    brutos = {c: v for c in CAMPOS_FILTRO if (v := request.query_params.get(c))}
    filtro = validar(FiltroTarefas, brutos)
    if not isinstance(filtro, FiltroTarefas):
        contexto: dict[str, Any] = {"filtros": brutos, "erros": filtro, "resultado": None}
        return _pagina(
            request, "tarefas/agenda.html", contexto | {"vencidas": [], "nomes": {}}, 422
        )
    resultado = service.listar_tarefas(session, filtro, pagina)
    # As vencidas da página ganham um título à parte, antes das outras (alerta interno, D7).
    vencidas = [t for t in resultado.itens if service.esta_vencida(t)]

    def link(numero: int) -> str:
        return "/tarefas?" + urlencode(brutos | {"pagina": numero})

    contexto = {
        "filtros": brutos,
        "erros": {},
        "resultado": resultado,
        "vencidas": vencidas,
        "proximas": [t for t in resultado.itens if t not in vencidas],
        "nomes": oportunidades.nomes_clientes(session, (t.cliente_id for t in resultado.itens)),
        "anterior": link(pagina - 1) if pagina > 1 else None,
        "proxima": link(pagina + 1) if resultado.tem_proxima else None,
    }
    return _pagina(request, "tarefas/agenda.html", contexto)


# --- criar e editar (só pendente, D8) ---


def _formulario(
    request: Request,
    session: Session,
    cliente_id: int,
    tarefa: Tarefa | None,
    dados: dict[str, str],
    erros: dict[str, str],
    status: int = 200,
) -> Response:
    lista = oportunidades.oportunidades_do_cliente(session, cliente_id)
    escolhida = dados.get("oportunidade_id", "")
    if escolhida.isdigit() and int(escolhida) not in {o.id for o in lista}:
        # Mais antiga que as listadas: sem ela, salvar o formulário apagaria o vínculo.
        antiga = session.get(Oportunidade, int(escolhida))
        if antiga is not None and antiga.cliente_id == cliente_id:
            lista.append(antiga)
    contexto: dict[str, Any] = {
        "tarefa": tarefa,
        "cliente": clientes.obter_cliente(session, cliente_id),
        "oportunidades": lista,
        "dados": dados,
        "erros": erros,
    }
    return _pagina(request, "tarefas/form.html", contexto, status)


@router.get("/tarefas/nova", response_class=HTMLResponse)
def nova(
    request: Request,
    session: SessionDep,
    cliente_id: Annotated[str | None, Query()] = None,
    oportunidade_id: Annotated[str | None, Query()] = None,
) -> Response:
    cliente = clientes.cliente_editavel(session, _id(cliente_id))
    dados = {"prioridade": "normal"}
    if oportunidade_id:
        oportunidade = oportunidades.obter_oportunidade(session, _id(oportunidade_id))
        if oportunidade.cliente_id != cliente.id:
            raise clientes.NaoEncontrado("oportunidade não encontrada")
        dados["oportunidade_id"] = str(oportunidade.id)
    return _formulario(request, session, cliente.id, None, dados, {})


@router.post("/tarefas")
async def criar(request: Request, session: SessionDep) -> Response:
    dados = await formulario(request, (*CAMPOS_TAREFA, "cliente_id"))
    cliente = clientes.cliente_editavel(session, _id(dados.pop("cliente_id", None)))
    entrada = _entrada(dados)
    try:
        if isinstance(entrada, TarefaIn):
            return ver(f"/tarefas/{service.criar_tarefa(session, cliente.id, entrada).id}")
    except RegraViolada as erro:
        session.rollback()
        entrada = {erro.campo: str(erro)}
    return _formulario(request, session, cliente.id, None, dados, entrada, 422)


def _pendente(session: Session, tarefa_id: int) -> Tarefa:
    tarefa = service.tarefa_editavel(session, tarefa_id)
    if tarefa.estado != "pendente":
        raise SoPendente
    return tarefa


class SoPendente(Exception):
    """Editar uma tarefa concluída ou cancelada: a tela pede para reabrir antes (409)."""


@router.get("/tarefas/{tarefa_id}/editar", response_class=HTMLResponse)
def editar(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    tarefa = _pendente(session, tarefa_id)
    dados = {
        "tipo": tarefa.tipo,
        "titulo": tarefa.titulo,
        "descricao": tarefa.descricao or "",
        "prioridade": tarefa.prioridade,
        "prazo": _prazo_no_formulario(tarefa.prazo),
        "oportunidade_id": str(tarefa.oportunidade_id or ""),
    }
    return _formulario(request, session, tarefa.cliente_id, tarefa, dados, {})


@router.post("/tarefas/{tarefa_id}")
async def atualizar(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    tarefa = _pendente(session, tarefa_id)
    dados = await formulario(request, CAMPOS_TAREFA)
    entrada = _entrada(dados)
    try:
        if isinstance(entrada, TarefaIn):
            service.atualizar_tarefa(session, tarefa_id, entrada)
            return ver(f"/tarefas/{tarefa_id}")
    except RegraViolada as erro:
        session.rollback()
        entrada = {erro.campo: str(erro)}
    return _formulario(request, session, tarefa.cliente_id, tarefa, dados, entrada, 422)


# --- detalhe e estado ---


def _detalhe(
    request: Request, session: Session, tarefa_id: int, status: int = 200, **extra: Any
) -> Response:
    tarefa = service.obter_tarefa(session, tarefa_id)
    oportunidade = (
        oportunidades.obter_oportunidade(session, tarefa.oportunidade_id)
        if tarefa.oportunidade_id
        else None
    )
    contexto: dict[str, Any] = {
        "tarefa": tarefa,
        "cliente": clientes.obter_cliente(session, tarefa.cliente_id),
        "oportunidade": oportunidade,
        "historico": service.eventos(session, tarefa_id),
        "erros": {},
    }
    return _pagina(request, "tarefas/detalhe.html", contexto | extra, status)


@router.get("/tarefas/{tarefa_id}", response_class=HTMLResponse)
def detalhe(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    return _detalhe(request, session, tarefa_id)


def _mudar(
    request: Request, session: Session, tarefa_id: int, acao: Callable[[Session, int], Tarefa]
) -> Response:
    try:
        acao(session, tarefa_id)
    except RegraViolada as erro:
        session.rollback()
        return _detalhe(request, session, tarefa_id, 422, erros={erro.campo: str(erro)})
    return ver(f"/tarefas/{tarefa_id}")


@router.post("/tarefas/{tarefa_id}/concluir")
def concluir(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    return _mudar(request, session, tarefa_id, service.concluir_tarefa)


@router.post("/tarefas/{tarefa_id}/cancelar")
def cancelar(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    return _mudar(request, session, tarefa_id, service.cancelar_tarefa)


@router.post("/tarefas/{tarefa_id}/reabrir")
def reabrir(request: Request, session: SessionDep, tarefa_id: IdDep) -> Response:
    return _mudar(request, session, tarefa_id, service.reabrir_tarefa)


# --- alerta interno e erros ---


def vencidas(request: Request) -> int | None:
    """Contador da navegação, calculado a cada página; nada roda em segundo plano (D7)."""
    try:
        with Session(request.app.state.engine) as session:
            return service.contar_vencidas(session)
    except OperationalError as erro:
        if "no such table" not in str(erro.orig):  # sem a 0004, a página inicial continua abrindo
            logger.warning("Falha ao calcular o contador de tarefas vencidas: %s", type(erro.orig))
        return None


def _tratar_so_pendente(request: Request, _erro: Exception) -> Response:
    contexto = {
        "titulo": "Tarefa fechada",
        "mensagem": "Só tarefas pendentes podem ser editadas. Reabra a tarefa antes.",
    }
    return _pagina(request, "clientes/erro.html", contexto, 409)


def configurar(app: FastAPI) -> None:
    app.include_router(router)
    app.add_exception_handler(SoPendente, _tratar_so_pendente)
    app.state.templates.env.globals["tarefas_vencidas"] = vencidas
    app.state.templates.env.filters["vencida"] = service.esta_vencida
