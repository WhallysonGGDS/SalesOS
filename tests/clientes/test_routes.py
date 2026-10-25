"""Rotas e telas de clientes (E5): banco temporário e dados fictícios."""

import re
import sqlite3
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import Response
from starlette.routing import BaseRoute

from salesos.features.clientes.schemas import TEXTO_LONGO_MAX
from salesos.security import CSRF_COOKIE, CSRF_FIELD, sign_token
from tests.conftest import TEST_SECRET

CLIENTE = {"tipo": "PJ", "nome": "Empresa Ficticia", "origem": "site"}
XSS = '<script>alert("x")</script>'


def _post(web: TestClient, url: str, **dados: str) -> Response:
    token = sign_token(TEST_SECRET, web.cookies[CSRF_COOKIE])
    resposta: Response = web.post(url, data={CSRF_FIELD: token, **dados}, follow_redirects=False)
    return resposta


def _criar(web: TestClient, **campos: str) -> int:
    resposta = _post(web, "/clientes", **(CLIENTE | campos))
    assert resposta.status_code == 303
    match = re.fullmatch(r"/clientes/(\d+)", resposta.headers["location"])
    assert match is not None
    return int(match.group(1))


def _consulta(db: Path, sql: str) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _dump(db: Path) -> list[str]:
    conn = sqlite3.connect(db)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


# --- lista, busca e paginação ---


def test_empty_list_renders(web: TestClient) -> None:
    resposta = web.get("/clientes")
    assert resposta.status_code == 200
    assert "Nenhum cliente" in resposta.text


def test_search_and_pagination_keep_the_query(web: TestClient) -> None:
    for i in range(25):
        _criar(web, nome=f"Loja {i:02d}")
    _criar(web, nome="Outra Empresa")
    primeira = web.get("/clientes", params={"q": "loja"})
    assert primeira.text.count('class="cliente"') == 20
    assert "Outra Empresa" not in primeira.text
    assert 'href="/clientes?q=loja&amp;pagina=2"' in primeira.text
    segunda = web.get("/clientes", params={"q": "loja", "pagina": 2})
    assert segunda.text.count('class="cliente"') == 5
    assert "pagina=3" not in segunda.text


@pytest.mark.parametrize(
    "params", [{"pagina": "0"}, {"pagina": "abc"}, {"pagina": "100001"}, {"q": "x" * 201}]
)
def test_list_rejects_invalid_query(web: TestClient, params: dict[str, str]) -> None:
    assert web.get("/clientes", params=params).status_code == 422


# --- criar e editar ---


def test_create_redirects_with_303_and_shows_detail(web: TestClient, db: Path) -> None:
    cliente_id = _criar(web, nome="Café Ficticio", email=" Contato@Exemplo.com ")
    detalhe = web.get(f"/clientes/{cliente_id}")
    assert detalhe.status_code == 200
    assert "Café Ficticio" in detalhe.text
    assert "contato@exemplo.com" in detalhe.text
    assert "Cliente criado" in detalhe.text


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ({"nome": "  "}, "Preencha este campo"),
        ({"email": "sem-arroba"}, "E-mail inválido"),
        ({"origem": "tiktok"}, "Valor inválido"),
        ({"nome": "x" * 201}, "Máximo de 200 caracteres"),
    ],
)
def test_invalid_client_form_returns_422_without_saving(
    web: TestClient, db: Path, campos: dict[str, str], mensagem: str
) -> None:
    resposta = _post(web, "/clientes", **(CLIENTE | campos))
    assert resposta.status_code == 422
    assert mensagem in resposta.text
    assert _consulta(db, "SELECT count(*) FROM clientes") == [(0,)]


def test_duplicate_email_message_does_not_reveal_the_other_client(web: TestClient) -> None:
    _criar(web, nome="Titular Secreto Ficticio", email="vendas@exemplo.com")
    resposta = _post(web, "/clientes", **(CLIENTE | {"email": "VENDAS@exemplo.com"}))
    assert resposta.status_code == 422
    assert "já usado" in resposta.text
    assert "Titular Secreto Ficticio" not in resposta.text


def test_blocked_fields_are_absent_and_ignored(web: TestClient, db: Path) -> None:
    for pagina in ("/clientes/novo", f"/clientes/{_criar(web)}/editar"):
        html = web.get(pagina).text
        assert 'name="documento"' not in html
        assert 'name="telefone"' not in html
    _criar(web, nome="Outra", documento="12345678901", telefone="11999999999")
    assert _consulta(db, "SELECT documento FROM clientes WHERE nome = 'Outra'") == [(None,)]


def test_edit_redirects_and_records_field_names(web: TestClient) -> None:
    cliente_id = _criar(web)
    resposta = _post(web, f"/clientes/{cliente_id}", **(CLIENTE | {"nome": "Nome Novo"}))
    assert resposta.status_code == 303
    assert resposta.headers["location"] == f"/clientes/{cliente_id}"
    detalhe = web.get(f"/clientes/{cliente_id}").text
    assert "Nome Novo" in detalhe
    assert "Cliente atualizado: nome" in detalhe


@pytest.mark.parametrize("url", ["/clientes/999", "/clientes/999/editar", "/contatos/999/editar"])
def test_missing_records_return_404_page(web: TestClient, url: str) -> None:
    resposta = web.get(url)
    assert resposta.status_code == 404
    assert "não encontrado" in resposta.text
    assert "Traceback" not in resposta.text


# --- arquivar e restaurar ---


def test_archive_and_restore(web: TestClient) -> None:
    cliente_id = _criar(web, nome="Arquivavel")
    assert _post(web, f"/clientes/{cliente_id}/arquivar").status_code == 303
    assert "Arquivavel" not in web.get("/clientes").text
    assert "Arquivavel" in web.get("/clientes", params={"arquivados": "1"}).text
    assert _post(web, f"/clientes/{cliente_id}/desarquivar").status_code == 303
    assert "Arquivavel" in web.get("/clientes").text


# --- contatos ---


def test_contact_lifecycle(web: TestClient, db: Path) -> None:
    cliente_id = _criar(web)
    resposta = _post(web, f"/clientes/{cliente_id}/contatos", nome="Pessoa Ficticia")
    assert resposta.status_code == 303
    ((contato_id,),) = _consulta(db, "SELECT id FROM contatos")
    assert "Pessoa Ficticia" in web.get(f"/clientes/{cliente_id}").text
    editar = _post(web, f"/contatos/{contato_id}", nome="Pessoa Ficticia", cargo="Compras")
    assert editar.status_code == 303
    assert editar.headers["location"] == f"/clientes/{cliente_id}"
    assert "Compras" in web.get(f"/clientes/{cliente_id}").text
    assert _post(web, f"/contatos/{contato_id}/remover").status_code == 303
    assert _consulta(db, "SELECT count(*) FROM contatos") == [(0,)]


def test_duplicate_contact_email_returns_422(web: TestClient) -> None:
    cliente_id = _criar(web)
    _post(web, f"/clientes/{cliente_id}/contatos", nome="A", email="p@exemplo.com")
    resposta = _post(web, f"/clientes/{cliente_id}/contatos", nome="B", email="P@exemplo.com")
    assert resposta.status_code == 422
    assert "já usado" in resposta.text


# --- interações ---


def test_interaction_is_recorded_in_timeline(web: TestClient, db: Path) -> None:
    cliente_id = _criar(web)
    resposta = _post(
        web,
        f"/clientes/{cliente_id}/interacoes",
        tipo="reuniao",
        ocorrida_em="2026-10-20T14:30",
        resumo="Reunião de apresentação",
    )
    assert resposta.status_code == 303
    assert "Reunião de apresentação" in web.get(f"/clientes/{cliente_id}").text
    ((ocorrida,),) = _consulta(db, "SELECT ocorrida_em FROM interacoes WHERE tipo = 'reuniao'")
    assert str(ocorrida).startswith("2026-10-20")


@pytest.mark.parametrize(
    "campos",
    [
        {"tipo": "sistema", "ocorrida_em": "2026-10-20T14:30", "resumo": "x"},
        {"tipo": "nota", "ocorrida_em": "ontem", "resumo": "x"},
        {"tipo": "nota", "ocorrida_em": "2026-10-20T14:30", "resumo": ""},
    ],
)
def test_invalid_interaction_returns_422(web: TestClient, db: Path, campos: dict[str, str]) -> None:
    cliente_id = _criar(web)
    resposta = _post(web, f"/clientes/{cliente_id}/interacoes", **campos)
    assert resposta.status_code == 422
    assert _consulta(db, "SELECT count(*) FROM interacoes WHERE tipo != 'sistema'") == [(0,)]


def _rotas(rotas: Sequence[BaseRoute]) -> Iterator[APIRoute]:
    """Todas as rotas, inclusive as de routers incluídos (FastAPI 0.147 não as copia)."""
    for rota in rotas:
        if isinstance(rota, APIRoute):
            yield rota
        elif incluido := getattr(rota, "original_router", None):
            yield from _rotas(incluido.routes)


def test_no_route_edits_or_deletes_interactions(web_app: FastAPI) -> None:
    caminhos = [r.path for r in _rotas(web_app.routes)]
    assert "/clientes/{cliente_id}/interacoes" in caminhos
    assert [p for p in caminhos if "interac" in p] == ["/clientes/{cliente_id}/interacoes"]
    rota = next(r for r in _rotas(web_app.routes) if "interac" in r.path)
    assert rota.methods == {"POST"}


# --- anonimização ---


def test_anonymization_requires_typing_the_id(web: TestClient, db: Path) -> None:
    cliente_id = _criar(web, nome="Pessoa Ficticia Anonimizavel")
    errado = _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id + 1))
    assert errado.status_code == 422
    assert _consulta(db, "SELECT anonimizado_em FROM clientes") == [(None,)]

    certo = _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id))
    assert certo.status_code == 303
    detalhe = web.get(f"/clientes/{cliente_id}").text
    assert f"Cliente anonimizado #{cliente_id}" in detalhe
    assert "Pessoa Ficticia Anonimizavel" not in detalhe
    assert 'action="/clientes/' not in detalhe  # nenhum formulário de alteração


def test_anonymized_client_refuses_every_change(web: TestClient) -> None:
    cliente_id = _criar(web)
    _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id))
    tentativas = [
        (f"/clientes/{cliente_id}", CLIENTE),
        (f"/clientes/{cliente_id}/desarquivar", {}),
        (f"/clientes/{cliente_id}/contatos", {"nome": "Pessoa"}),
        (
            f"/clientes/{cliente_id}/interacoes",
            {"tipo": "nota", "ocorrida_em": "2026-10-20T14:30", "resumo": "x"},
        ),
    ]
    for url, dados in tentativas:
        resposta = _post(web, url, **dados)
        assert resposta.status_code == 409, url
        assert "anonimizado" in resposta.text
    assert web.get(f"/clientes/{cliente_id}/editar").status_code == 409


# --- segurança transversal ---


def _urls(app: FastAPI, metodo: str, cliente_id: int, contato_id: int) -> list[str]:
    return [
        r.path.replace("{cliente_id}", str(cliente_id)).replace("{contato_id}", str(contato_id))
        for r in _rotas(app.routes)
        if metodo in (r.methods or set())
    ]


@pytest.fixture
def com_dados(web: TestClient, db: Path) -> tuple[int, int]:
    cliente_id = _criar(web)
    _post(web, f"/clientes/{cliente_id}/contatos", nome="Pessoa Ficticia")
    ((contato_id,),) = _consulta(db, "SELECT id FROM contatos")
    return cliente_id, int(contato_id)


def test_every_post_route_requires_csrf(
    web: TestClient, web_app: FastAPI, db: Path, com_dados: tuple[int, int]
) -> None:
    urls = _urls(web_app, "POST", *com_dados)
    assert len(urls) >= 9
    antes = _dump(db)
    for url in urls:
        sem_token = web.post(url, data={"nome": "Invasor", "confirmacao": str(com_dados[0])})
        assert sem_token.status_code == 403, url
        falso = web.post(url, data={CSRF_FIELD: "falso", "confirmacao": str(com_dados[0])})
        assert falso.status_code == 403, url
    assert _dump(db) == antes


def test_get_routes_have_no_side_effects(
    web: TestClient, web_app: FastAPI, db: Path, com_dados: tuple[int, int]
) -> None:
    urls = _urls(web_app, "GET", *com_dados)
    assert len(urls) >= 5
    antes = _dump(db)
    for url in urls:
        assert web.get(url).status_code == 200, url
    assert _dump(db) == antes


def test_user_content_is_escaped_everywhere(web: TestClient, db: Path) -> None:
    cliente_id = _criar(web, nome=XSS, nome_fantasia=XSS, observacoes=XSS)
    _post(web, f"/clientes/{cliente_id}/contatos", nome=XSS, cargo=XSS)
    _post(
        web,
        f"/clientes/{cliente_id}/interacoes",
        tipo="nota",
        ocorrida_em="2026-10-20T14:30",
        resumo=XSS,
    )
    ((contato_id,),) = _consulta(db, "SELECT id FROM contatos")
    for url in (
        "/clientes",
        f"/clientes/{cliente_id}",
        f"/clientes/{cliente_id}/editar",
        f"/contatos/{contato_id}/editar",
    ):
        html = web.get(url).text
        assert "<script>alert" not in html, url
        assert "&lt;script&gt;" in html, url
    invalido = _post(web, "/clientes", **(CLIENTE | {"nome": XSS, "email": "invalido"}))
    assert invalido.status_code == 422
    assert "<script>alert" not in invalido.text


def test_new_client_must_choose_an_origin(web: TestClient, db: Path) -> None:
    assert '<option value="" selected>' in web.get("/clientes/novo").text
    resposta = _post(web, "/clientes", tipo="PJ", nome="Sem Origem", origem="")
    assert resposta.status_code == 422
    assert "Preencha este campo" in resposta.text
    assert _consulta(db, "SELECT count(*) FROM clientes") == [(0,)]


def test_largest_legitimate_form_fits_the_body_limit(web: TestClient) -> None:
    """Todos os campos no máximo, com caracteres de 4 bytes (viram 12 bytes no formulário)."""
    grande = "\U0001f600"
    cliente_id = _criar(
        web,
        nome=grande * 200,
        nome_fantasia=grande * 200,
        observacoes=grande * TEXTO_LONGO_MAX,
    )
    assert (
        _post(
            web,
            f"/clientes/{cliente_id}/interacoes",
            tipo="nota",
            ocorrida_em="2026-10-20T14:30",
            resumo=grande * TEXTO_LONGO_MAX,
        ).status_code
        == 303
    )
