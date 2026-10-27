"""Páginas HTML para 403 (CSRF) e 422 (endereço inválido) quando o navegador pede HTML.

Proposta G (estabilização, E6). Quem não pede HTML (`Accept` sem `text/html`: APIs, scripts)
continua com JSON: o 403 é o padrão do FastAPI; o 422 tem o mesmo formato, sem o campo
`input`. As mensagens são fixas: nenhuma resposta repete o que foi enviado. O 413 nasce
fora da aplicação, em `security.LimiteCorpo`.
"""

from typing import cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from salesos.formularios import renderizar
from salesos.security import quer_html


def _pagina(request: Request, titulo: str, mensagem: str, status: int) -> Response:
    contexto = {"titulo": titulo, "mensagem": mensagem}
    return renderizar(request, "clientes/erro.html", contexto, status)


async def _http(request: Request, excecao: Exception) -> Response:
    erro = cast(HTTPException, excecao)  # registrado só para HTTPException
    if erro.status_code == 403 and quer_html(request.headers.get("accept", "")):
        return _pagina(request, "Formulário expirado", str(erro.detail), 403)
    return await http_exception_handler(request, erro)


async def _validacao(request: Request, excecao: Exception) -> Response:
    erro = cast(RequestValidationError, excecao)  # registrado só para RequestValidationError
    if quer_html(request.headers.get("accept", "")):
        mensagem = "Endereço inválido. Volte e use os links e botões das páginas."
        return _pagina(request, "Endereço inválido", mensagem, 422)
    # Mesmo formato do FastAPI (`loc`, `msg`, `type`, `ctx`), sem `input`: o valor enviado
    # não volta na resposta.
    detalhes = [{k: v for k, v in item.items() if k != "input"} for item in erro.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(detalhes)})


def configurar(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http)
    app.add_exception_handler(RequestValidationError, _validacao)
