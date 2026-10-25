import asyncio
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from starlette.types import Message

from salesos.security import CSRF_COOKIE, CSRF_FIELD, CSRF_HEADER, LIMITE_CORPO, sign_token
from tests.conftest import TEST_SECRET


@pytest.fixture
def form_client(app: FastAPI, client: TestClient) -> TestClient:
    """Cliente com uma rota POST de teste; a proteção CSRF vale para toda a aplicação."""

    @app.api_route("/_teste", methods=["POST", "PUT", "PATCH", "DELETE"])
    def _rota_de_teste() -> dict[str, bool]:
        return {"ok": True}

    return client


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "127.0.0.1:8000", "[::1]"])
def test_loopback_hosts_are_accepted(client: TestClient, host: str) -> None:
    assert client.get("/health", headers={"host": host}).status_code == 200


@pytest.mark.parametrize("host", ["evil.example.com", "192.168.0.10", "salesos.local"])
def test_unknown_host_is_rejected(client: TestClient, host: str) -> None:
    assert client.get("/health", headers={"host": host}).status_code == 400


@pytest.mark.parametrize("path", ["/", "/health"])
def test_security_headers_are_present(client: TestClient, path: str) -> None:
    headers = client.get(path).headers
    assert headers["cache-control"] == "no-store"  # páginas com dados pessoais fora do cache
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"


def test_csrf_cookie_is_issued_with_safe_attributes(client: TestClient) -> None:
    set_cookie = client.get("/").headers["set-cookie"]
    assert set_cookie.startswith(f"{CSRF_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Path=/" in set_cookie


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_unsafe_methods_without_csrf_are_rejected(form_client: TestClient, method: str) -> None:
    form_client.get("/")
    assert form_client.request(method, "/_teste").status_code == 403


def test_post_with_cookie_but_no_token_is_rejected(form_client: TestClient) -> None:
    form_client.get("/")
    assert form_client.post("/_teste", data={"campo": "x"}).status_code == 403


def test_post_with_forged_token_is_rejected(form_client: TestClient) -> None:
    form_client.get("/")
    cookie = form_client.cookies[CSRF_COOKIE]
    forged = sign_token("outro-segredo", cookie)
    response = form_client.post("/_teste", data={CSRF_FIELD: forged})
    assert response.status_code == 403


def test_post_with_valid_form_token_is_accepted(form_client: TestClient) -> None:
    form_client.get("/")
    token = sign_token(TEST_SECRET, form_client.cookies[CSRF_COOKIE])
    response = form_client.post("/_teste", data={CSRF_FIELD: token, "nome": "Cliente Ficticio"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_post_with_valid_header_token_is_accepted(form_client: TestClient) -> None:
    form_client.get("/")
    token = sign_token(TEST_SECRET, form_client.cookies[CSRF_COOKIE])
    assert form_client.post("/_teste", headers={CSRF_HEADER: token}).status_code == 200


def test_token_rendered_by_template_global_is_accepted(
    app: FastAPI, form_client: TestClient
) -> None:
    templates = app.state.templates

    @app.get("/_formulario", response_class=PlainTextResponse)
    def _formulario(request: Request) -> str:
        return str(templates.env.from_string("{{ csrf_token(request) }}").render(request=request))

    form_client.get("/")
    token = form_client.get("/_formulario").text
    assert form_client.post("/_teste", data={CSRF_FIELD: token}).status_code == 200


def test_first_post_without_cookie_is_rejected(form_client: TestClient) -> None:
    assert form_client.post("/_teste", data={CSRF_FIELD: "qualquer"}).status_code == 403


def test_get_does_not_require_csrf(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def _token(cliente: TestClient) -> str:
    cliente.get("/")
    return sign_token(TEST_SECRET, cliente.cookies[CSRF_COOKIE])


def _form(token: str, tamanho: int) -> bytes:
    """Corpo urlencoded com exatamente `tamanho` bytes."""
    inicio = f"{CSRF_FIELD}={token}&campo=".encode()
    return inicio + b"x" * (tamanho - len(inicio))


FORM = {"content-type": "application/x-www-form-urlencoded"}


def test_body_above_limit_is_rejected_even_with_valid_token(form_client: TestClient) -> None:
    corpo = _form(_token(form_client), LIMITE_CORPO + 1)
    resposta = form_client.post("/_teste", content=corpo, headers=FORM)
    assert resposta.status_code == 413
    assert resposta.headers["cache-control"] == "no-store"


def test_chunked_body_above_limit_is_rejected(form_client: TestClient) -> None:
    """Sem Content-Length (transferência em blocos), o limite vale contando os bytes."""
    corpo = _form(_token(form_client), LIMITE_CORPO + 1)

    def blocos() -> Iterator[bytes]:
        for i in range(0, len(corpo), 4096):
            yield corpo[i : i + 4096]

    resposta = form_client.post("/_teste", content=blocos(), headers=FORM)
    assert resposta.request.headers.get("content-length") is None
    assert resposta.status_code == 413


def test_body_at_limit_with_valid_token_is_accepted(form_client: TestClient) -> None:
    corpo = _form(_token(form_client), LIMITE_CORPO)
    resposta = form_client.post("/_teste", content=corpo, headers=FORM)
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


def test_client_disconnect_mid_body_is_not_a_server_error(app: FastAPI) -> None:
    """Cliente que desiste no meio do envio: nenhuma resposta e nenhuma exceção (sem 500)."""
    mensagens: list[Message] = [
        {"type": "http.request", "body": b"csrf_token=x", "more_body": True},
        {"type": "http.disconnect"},
    ]
    enviados: list[Message] = []

    async def receive() -> Message:
        return mensagens.pop(0)

    async def send(mensagem: Message) -> None:
        enviados.append(mensagem)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/clientes",
        "raw_path": b"/clientes",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"127.0.0.1"),
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
    }
    asyncio.run(app(scope, receive, send))
    assert enviados == []
