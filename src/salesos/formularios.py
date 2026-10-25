"""Auxiliares das rotas com formulários HTML, compartilhados pelas features.

Leitura só dos campos permitidos, validação com mensagens por campo (sem repetir o valor
enviado), resposta 303 e datas: UTC no banco, fuso deste computador na tela.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, ValidationError


def renderizar(
    request: Request, nome: str, contexto: dict[str, Any], status: int = 200
) -> Response:
    resposta: Response = request.app.state.templates.TemplateResponse(
        request, nome, contexto, status_code=status
    )
    return resposta


def ver(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


async def formulario(request: Request, campos: tuple[str, ...]) -> dict[str, str]:
    form = await request.form()
    return {c: v for c in campos if isinstance(v := form.get(c), str)}


class Mensagem(ValueError):
    """Erro de validação cujo texto aparece como está no campo do formulário."""


def erros(erro: ValidationError) -> dict[str, str]:
    """Mensagens por campo, sem repetir o valor enviado."""
    mensagens: dict[str, str] = {}
    for item in erro.errors():
        campo = str(item["loc"][0]) if item["loc"] else "geral"
        tipo, ctx = item["type"], item.get("ctx") or {}
        if isinstance(ctx.get("error"), Mensagem):
            texto = str(ctx["error"])
        elif tipo == "string_too_long":
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


def validar[M: BaseModel](modelo: type[M], dados: dict[str, Any]) -> M | dict[str, str]:
    try:
        return modelo.model_validate(dados)
    except ValidationError as erro:
        return erros(erro)


def data_local(valor: datetime | None) -> str:
    """Datas ficam em UTC no banco e aparecem no fuso deste computador."""
    if valor is None:
        return ""
    return valor.replace(tzinfo=UTC).astimezone().strftime("%d/%m/%Y %H:%M")


def data_iso(valor: datetime | None) -> str:
    """Valor de `<time datetime>`: o banco guarda UTC sem fuso."""
    return "" if valor is None else valor.strftime("%Y-%m-%dT%H:%M:%SZ")


def hora_local(valor: str) -> datetime | str:
    """`datetime-local` não tem fuso: é interpretado no fuso deste computador."""
    try:
        return datetime.fromisoformat(valor).astimezone()
    except ValueError:
        return valor  # o schema recusa com a mensagem do campo
