"""Rotas e telas de clientes (Fase 02, E5).

Rotas finas: validam a entrada com os schemas, chamam o serviço e respondem com 303 depois
de cada POST bem-sucedido. O CSRF vale para todas pela dependência global da aplicação.
Não existe rota para editar ou excluir interações (D5).
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from salesos.db import get_session
from salesos.features.clientes import service
from salesos.features.clientes.models import ORIGENS, TIPOS_INTERACAO
from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]

# Só estes campos são lidos dos formulários: documento e telefone nunca entram (D6, D11, D12).
CAMPOS_CLIENTE = ("tipo", "nome", "nome_fantasia", "email", "origem", "observacoes")
CAMPOS_CONTATO = ("nome", "cargo", "email")
CAMPOS_INTERACAO = ("tipo", "ocorrida_em", "resumo", "contato_id")
TIPOS_MANUAIS = tuple(t for t in TIPOS_INTERACAO if t != "sistema")
ROTULOS = {
    "PF": "Pessoa física",
    "PJ": "Pessoa jurídica",
    "indicacao": "Indicação",
    "site": "Site",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "whatsapp": "WhatsApp",
    "evento": "Evento",
    "prospeccao_ativa": "Prospecção ativa",
    "outro": "Outro",
    "ligacao": "Ligação",
    "reuniao": "Reunião",
    "mensagem": "Mensagem",
    "email": "E-mail",
    "nota": "Nota",
    "sistema": "Sistema",
}


def _pagina(request: Request, nome: str, contexto: dict[str, Any], status: int = 200) -> Response:
    templates = request.app.state.templates
    base = {
        "origens": ORIGENS,
        "tipos_interacao": TIPOS_MANUAIS,
        "rotulos": ROTULOS,
        "secao": "clientes",
    }
    resposta: Response = templates.TemplateResponse(
        request, nome, base | contexto, status_code=status
    )
    return resposta


def _ver(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


async def _formulario(request: Request, campos: tuple[str, ...]) -> dict[str, str]:
    form = await request.form()
    return {c: v for c in campos if isinstance(v := form.get(c), str)}


def _erros(erro: ValidationError) -> dict[str, str]:
    """Mensagens por campo, sem repetir o valor enviado."""
    mensagens: dict[str, str] = {}
    for item in erro.errors():
        campo = str(item["loc"][0]) if item["loc"] else "geral"
        tipo, ctx = item["type"], item.get("ctx") or {}
        if tipo == "string_too_long":
            texto = f"Máximo de {ctx.get('max_length')} caracteres"
        elif tipo in ("missing", "string_too_short", "string_type"):
            texto = "Preencha este campo"
        elif campo == "email":
            texto = "E-mail inválido"
        elif campo == "ocorrida_em":
            texto = "Informe data e hora válidas"
        else:
            texto = "Valor inválido"
        mensagens.setdefault(campo, texto)
    return mensagens


def _validar[M: BaseModel](modelo: type[M], dados: dict[str, Any]) -> M | dict[str, str]:
    try:
        return modelo.model_validate(dados)
    except ValidationError as erro:
        return _erros(erro)


def data_local(valor: datetime | None) -> str:
    """Datas ficam em UTC no banco e aparecem no fuso deste computador."""
    if valor is None:
        return ""
    return valor.replace(tzinfo=UTC).astimezone().strftime("%d/%m/%Y %H:%M")


def data_iso(valor: datetime | None) -> str:
    """Valor de `<time datetime>`: o banco guarda UTC sem fuso."""
    return "" if valor is None else valor.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hora_local(valor: str) -> datetime | str:
    """`datetime-local` não tem fuso: é interpretado no fuso deste computador."""
    try:
        return datetime.fromisoformat(valor).astimezone()
    except ValueError:
        return valor  # o schema recusa com a mensagem do campo


# --- lista ---


@router.get("/clientes", response_class=HTMLResponse)
def lista(
    request: Request,
    session: SessionDep,
    q: Annotated[str, Query(max_length=200)] = "",
    arquivados: bool = False,
    pagina: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> Response:
    resultado = service.listar_clientes(session, q, arquivados, pagina)
    filtros = {k: v for k, v in (("q", q), ("arquivados", "1" if arquivados else "")) if v}

    def link(numero: int) -> str:
        return "/clientes?" + urlencode(filtros | {"pagina": numero})

    return _pagina(
        request,
        "clientes/lista.html",
        {
            "resultado": resultado,
            "q": q,
            "arquivados": arquivados,
            "anterior": link(pagina - 1) if pagina > 1 else None,
            "proxima": link(pagina + 1) if resultado.tem_proxima else None,
        },
    )


# --- criar e editar cliente ---


@router.get("/clientes/novo", response_class=HTMLResponse)
def novo(request: Request) -> Response:
    return _pagina(request, "clientes/form.html", {"cliente": None, "dados": {}, "erros": {}})


@router.post("/clientes")
async def criar(request: Request, session: SessionDep) -> Response:
    dados = await _formulario(request, CAMPOS_CLIENTE)
    entrada = _validar(ClienteIn, dados)
    try:
        if isinstance(entrada, ClienteIn):
            return _ver(f"/clientes/{service.criar_cliente(session, entrada).id}")
    except service.Duplicado as erro:
        entrada = {"email": str(erro)}
    contexto = {"cliente": None, "dados": dados, "erros": entrada}
    return _pagina(request, "clientes/form.html", contexto, 422)


@router.get("/clientes/{cliente_id}/editar", response_class=HTMLResponse)
def editar(request: Request, session: SessionDep, cliente_id: int) -> Response:
    cliente = service.cliente_editavel(session, cliente_id)
    dados = {c: getattr(cliente, c) or "" for c in CAMPOS_CLIENTE}
    return _pagina(request, "clientes/form.html", {"cliente": cliente, "dados": dados, "erros": {}})


@router.post("/clientes/{cliente_id}")
async def atualizar(request: Request, session: SessionDep, cliente_id: int) -> Response:
    cliente = service.cliente_editavel(session, cliente_id)
    dados = await _formulario(request, CAMPOS_CLIENTE)
    entrada = _validar(ClienteIn, dados)
    try:
        if isinstance(entrada, ClienteIn):
            service.atualizar_cliente(session, cliente_id, entrada)
            return _ver(f"/clientes/{cliente_id}")
    except service.Duplicado as erro:
        entrada = {"email": str(erro)}
    contexto = {"cliente": cliente, "dados": dados, "erros": entrada}
    return _pagina(request, "clientes/form.html", contexto, 422)


# --- detalhe, arquivar e anonimizar ---


def _detalhe(
    request: Request, session: Session, cliente_id: int, status: int = 200, **extra: Any
) -> Response:
    cliente = service.obter_cliente(session, cliente_id)
    contatos = service.listar_contatos(session, cliente_id)
    contexto = {
        "cliente": cliente,
        "contatos": contatos,
        "nomes_contatos": {c.id: c.nome for c in contatos},
        "linha": service.listar_interacoes(session, cliente_id),
        "agora": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "contato": {},
        "erros_contato": {},
        "interacao": {},
        "erros_interacao": {},
        "erro_anonimizar": None,
    }
    return _pagina(request, "clientes/detalhe.html", contexto | extra, status)


@router.get("/clientes/{cliente_id}", response_class=HTMLResponse)
def detalhe(request: Request, session: SessionDep, cliente_id: int) -> Response:
    return _detalhe(request, session, cliente_id)


@router.post("/clientes/{cliente_id}/arquivar")
def arquivar(session: SessionDep, cliente_id: int) -> Response:
    service.arquivar_cliente(session, cliente_id)
    return _ver(f"/clientes/{cliente_id}")


@router.post("/clientes/{cliente_id}/desarquivar")
def desarquivar(session: SessionDep, cliente_id: int) -> Response:
    service.desarquivar_cliente(session, cliente_id)
    return _ver(f"/clientes/{cliente_id}")


@router.post("/clientes/{cliente_id}/anonimizar")
async def anonimizar(request: Request, session: SessionDep, cliente_id: int) -> Response:
    confirmacao = (await _formulario(request, ("confirmacao",))).get("confirmacao", "")
    if confirmacao.strip() != str(cliente_id):
        mensagem = f"Para confirmar, digite o número {cliente_id}."
        return _detalhe(request, session, cliente_id, 422, erro_anonimizar=mensagem)
    service.anonimizar_cliente(session, cliente_id)
    return _ver(f"/clientes/{cliente_id}")


# --- contatos ---


@router.post("/clientes/{cliente_id}/contatos")
async def adicionar_contato(request: Request, session: SessionDep, cliente_id: int) -> Response:
    service.cliente_editavel(session, cliente_id)
    dados = await _formulario(request, CAMPOS_CONTATO)
    entrada = _validar(ContatoIn, dados)
    try:
        if isinstance(entrada, ContatoIn):
            service.adicionar_contato(session, cliente_id, entrada)
            return _ver(f"/clientes/{cliente_id}#contatos")
    except service.Duplicado as erro:
        entrada = {"email": str(erro)}
    return _detalhe(request, session, cliente_id, 422, contato=dados, erros_contato=entrada)


@router.get("/contatos/{contato_id}/editar", response_class=HTMLResponse)
def editar_contato(request: Request, session: SessionDep, contato_id: int) -> Response:
    contato = service.obter_contato(session, contato_id)
    dados = {c: getattr(contato, c) or "" for c in CAMPOS_CONTATO}
    contexto = {"contato": contato, "dados": dados, "erros": {}}
    return _pagina(request, "clientes/contato.html", contexto)


@router.post("/contatos/{contato_id}")
async def atualizar_contato(request: Request, session: SessionDep, contato_id: int) -> Response:
    contato = service.obter_contato(session, contato_id)
    dados = await _formulario(request, CAMPOS_CONTATO)
    entrada = _validar(ContatoIn, dados)
    try:
        if isinstance(entrada, ContatoIn):
            service.atualizar_contato(session, contato_id, entrada)
            return _ver(f"/clientes/{contato.cliente_id}")
    except service.Duplicado as erro:
        entrada = {"email": str(erro)}
    contexto = {"contato": contato, "dados": dados, "erros": entrada}
    return _pagina(request, "clientes/contato.html", contexto, 422)


@router.post("/contatos/{contato_id}/remover")
def remover_contato(session: SessionDep, contato_id: int) -> Response:
    cliente_id = service.obter_contato(session, contato_id).cliente_id
    service.remover_contato(session, contato_id)
    return _ver(f"/clientes/{cliente_id}#contatos")


# --- interações (só acréscimo) ---


@router.post("/clientes/{cliente_id}/interacoes")
async def registrar_interacao(request: Request, session: SessionDep, cliente_id: int) -> Response:
    service.cliente_editavel(session, cliente_id)
    dados = await _formulario(request, CAMPOS_INTERACAO)
    bruto: dict[str, Any] = dict(dados)
    if "ocorrida_em" in dados:
        bruto["ocorrida_em"] = _hora_local(dados["ocorrida_em"])
    entrada = _validar(InteracaoIn, bruto)
    if isinstance(entrada, InteracaoIn):
        service.registrar_interacao(session, cliente_id, entrada)
        return _ver(f"/clientes/{cliente_id}#linha")
    return _detalhe(request, session, cliente_id, 422, interacao=dados, erros_interacao=entrada)


# --- erros sem dados pessoais ---


def _tratar_nao_encontrado(request: Request, _erro: Exception) -> Response:
    contexto = {"titulo": "Registro não encontrado", "mensagem": "Registro não encontrado."}
    return _pagina(request, "clientes/erro.html", contexto, 404)


def _tratar_bloqueado(request: Request, _erro: Exception) -> Response:
    mensagem = "Este cliente foi anonimizado e não aceita alterações."
    return _pagina(
        request, "clientes/erro.html", {"titulo": "Cliente anonimizado", "mensagem": mensagem}, 409
    )


def configurar(app: FastAPI) -> None:
    app.include_router(router)
    app.add_exception_handler(service.NaoEncontrado, _tratar_nao_encontrado)
    app.add_exception_handler(service.Bloqueado, _tratar_bloqueado)
    app.state.templates.env.filters["data_local"] = data_local
    app.state.templates.env.filters["data_iso"] = data_iso
