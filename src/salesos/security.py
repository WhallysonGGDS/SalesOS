"""Proteções HTTP da aplicação local: cabeçalhos de segurança e CSRF (double-submit assinado).

O cookie guarda um token aleatório (HttpOnly). Formulários e requisições enviam a assinatura
HMAC desse token com o segredo da aplicação, no campo `csrf_token` ou no header `X-CSRF-Token`.
"""

import hashlib
import hmac
import secrets
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSRF_COOKIE = "salesos_csrf"
CSRF_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# O maior formulário legítimo (5.000 caracteres de 4 bytes, codificados) tem cerca de 65 KB.
LIMITE_CORPO = 256 * 1024

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; object-src 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    # As páginas mostram dados pessoais: nada fica no cache do navegador depois de anonimizar.
    "Cache-Control": "no-store",
}


def sign_token(secret: str, token: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def _secret(request: Request) -> str:
    secret: str = request.app.state.settings.secret_key.get_secret_value()
    return secret


def form_token(request: Request) -> str:
    """Token para o campo oculto `csrf_token` dos formulários (global dos templates)."""
    return sign_token(_secret(request), request.state.csrf_token)


async def security_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    token = request.cookies.get(CSRF_COOKIE)
    issue_cookie = token is None
    request.state.csrf_token = token or secrets.token_urlsafe(32)
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    if issue_cookie:
        response.set_cookie(
            CSRF_COOKIE, request.state.csrf_token, httponly=True, samesite="strict", path="/"
        )
    return response


async def require_csrf(request: Request) -> None:
    """Dependência global: métodos que alteram estado exigem token CSRF válido."""
    if request.method not in UNSAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    submitted: object = request.headers.get(CSRF_HEADER)
    if submitted is None and request.headers.get("content-type", "").startswith(
        ("application/x-www-form-urlencoded", "multipart/form-data")
    ):
        submitted = (await request.form()).get(CSRF_FIELD)
    if not (
        cookie
        and isinstance(submitted, str)
        and hmac.compare_digest(submitted, sign_token(_secret(request), cookie))
    ):
        raise HTTPException(
            status_code=403,
            detail="Formulário expirado ou inválido. Recarregue a página e envie de novo.",
        )


class LimiteCorpo:
    """Recusa com 413 corpos maiores que `LIMITE_CORPO`, antes de qualquer leitura de formulário.

    O corpo é lido aqui, até o limite, e entregue inteiro à aplicação. Vale com ou sem
    Content-Length e protege tanto o CSRF quanto as rotas que leem o formulário.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        corpo = bytearray()
        while True:
            mensagem = await receive()
            if mensagem["type"] == "http.disconnect":
                return
            corpo += mensagem.get("body", b"")
            if len(corpo) > LIMITE_CORPO:
                await _muito_grande(scope, receive, send)
                return
            if not mensagem.get("more_body", False):
                break
        entregue = False

        async def reenviar() -> Message:
            nonlocal entregue
            if entregue:
                return await receive()  # depois do corpo, só o aviso de desconexão
            entregue = True
            return {"type": "http.request", "body": bytes(corpo), "more_body": False}

        await self.app(scope, reenviar, send)


async def _muito_grande(scope: Scope, receive: Receive, send: Send) -> None:
    resposta = PlainTextResponse(
        "Envio grande demais. Reduza o texto e tente de novo.",
        status_code=413,
        headers=SECURITY_HEADERS,
    )
    await resposta(scope, receive, send)
