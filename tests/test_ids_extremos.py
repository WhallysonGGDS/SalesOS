"""Nenhuma rota com id no caminho responde 500 a ids fora do inteiro de 64 bits (E1)."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from salesos.config import Settings
from salesos.main import create_app
from salesos.security import CSRF_COOKIE, CSRF_FIELD, sign_token
from tests.conftest import TEST_SECRET, migrar
from tests.oportunidades.test_routes import _rotas

IDS = ["0", "-1", str(2**63), "99999999999999999999"]
PARAMETRO = re.compile(r"\{[a-z_]+_id\}")


@pytest.fixture
def web(tmp_path: Path, settings: Settings) -> Iterator[tuple[FastAPI, TestClient]]:
    migrar(tmp_path / "teste.db")
    app = create_app(settings)
    # Sem relançar a exceção: o que interessa é o status que o navegador veria.
    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as cliente:
        cliente.get("/clientes")  # recebe o cookie CSRF
        yield app, cliente


def _com_id(app: FastAPI, metodo: str) -> list[str]:
    return sorted(
        r.path
        for r in _rotas(app.routes)
        if PARAMETRO.search(r.path) and metodo in (r.methods or set())
    )


def test_every_route_with_an_id_is_covered(web: tuple[FastAPI, TestClient]) -> None:
    # Garante que o percurso abaixo não ficou vazio nem esqueceu clientes e contatos.
    app, _ = web
    caminhos = _com_id(app, "GET") + _com_id(app, "POST")
    assert any(c.startswith("/clientes/{cliente_id}") for c in caminhos)
    assert any(c.startswith("/contatos/{contato_id}") for c in caminhos)
    assert len(caminhos) >= 20


@pytest.mark.parametrize("ident", IDS)
def test_out_of_range_ids_never_give_500(web: tuple[FastAPI, TestClient], ident: str) -> None:
    app, cliente = web
    token = sign_token(TEST_SECRET, cliente.cookies[CSRF_COOKIE])
    falhas = []
    for metodo in ("GET", "POST"):
        for caminho in _com_id(app, metodo):
            url = PARAMETRO.sub(ident, caminho)
            if metodo == "GET":
                resposta = cliente.get(url)
            else:
                dados = {CSRF_FIELD: token, "confirmacao": ident, "titulo": "X"}
                resposta = cliente.post(url, data=dados, follow_redirects=False)
            if resposta.status_code not in (404, 422):
                falhas.append(f"{metodo} {url} -> {resposta.status_code}")
    assert falhas == []


@pytest.mark.parametrize("ident", [str(2**63), "99999999999999999999", "-9999999999999999999"])
def test_out_of_range_contact_in_the_interaction_form_is_422(
    web: tuple[FastAPI, TestClient], ident: str
) -> None:
    # Ids também chegam pelo corpo do formulário, não só pelo caminho.
    _, cliente = web
    token = sign_token(TEST_SECRET, cliente.cookies[CSRF_COOKIE])
    novo = {CSRF_FIELD: token, "tipo": "PJ", "nome": "Empresa Ficticia", "origem": "site"}
    local = cliente.post("/clientes", data=novo, follow_redirects=False).headers["location"]
    dados = {
        CSRF_FIELD: token,
        "tipo": "ligacao",
        "ocorrida_em": "2026-01-01T10:00",
        "resumo": "Resumo ficticio",
        "contato_id": ident,
    }
    resposta = cliente.post(f"{local}/interacoes", data=dados, follow_redirects=False)
    assert resposta.status_code == 422
