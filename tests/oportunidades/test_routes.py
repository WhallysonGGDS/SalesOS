"""Rotas e telas do funil: CSRF, 303, 422 no campo, XSS, 404/409 e GET sem efeito."""

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

from salesos.config import Settings
from salesos.main import create_app
from salesos.security import CSRF_COOKIE, CSRF_FIELD, sign_token
from tests.conftest import TEST_SECRET, migrar

XSS = '<script>alert("x")</script>'


@pytest.fixture
def db(tmp_path: Path) -> Path:
    caminho = tmp_path / "teste.db"
    migrar(caminho)
    return caminho


@pytest.fixture
def web_app(db: Path, settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def web(web_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(web_app, base_url="http://127.0.0.1") as cliente:
        cliente.get("/oportunidades")  # recebe o cookie CSRF
        yield cliente


def _post(web: TestClient, url: str, **dados: str) -> Response:
    token = sign_token(TEST_SECRET, web.cookies[CSRF_COOKIE])
    resposta: Response = web.post(url, data={CSRF_FIELD: token, **dados}, follow_redirects=False)
    return resposta


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


def _cliente(web: TestClient, nome: str = "Empresa Ficticia") -> int:
    resposta = _post(web, "/clientes", tipo="PJ", nome=nome, origem="site")
    return int(resposta.headers["location"].rsplit("/", 1)[1])


def _criar(web: TestClient, cliente_id: int | None = None, **campos: str) -> int:
    cliente_id = cliente_id or _cliente(web)
    dados = {
        "cliente_id": str(cliente_id),
        "titulo": "Projeto ficticio",
        "valor_centavos": "1.234,56",
    }
    resposta = _post(web, "/oportunidades", **(dados | campos))
    assert resposta.status_code == 303, resposta.text
    match = re.fullmatch(r"/oportunidades/(\d+)", resposta.headers["location"])
    assert match is not None
    return int(match.group(1))


def test_empty_funnel_invites_to_create_from_a_client(web: TestClient) -> None:
    resposta = web.get("/oportunidades")
    assert resposta.status_code == 200
    assert "Nenhuma oportunidade" in resposta.text
    assert 'href="/oportunidades" aria-current="page"' in resposta.text
    assert "default-src 'self'" in resposta.headers["content-security-policy"]


def test_create_shows_value_stage_and_history(web: TestClient, db: Path) -> None:
    oportunidade_id = _criar(web)
    detalhe = web.get(f"/oportunidades/{oportunidade_id}").text
    assert "R$ 1.234,56" in detalhe
    assert "Novo lead" in detalhe
    assert _consulta(db, "SELECT valor_centavos, etapa FROM oportunidades") == [
        (123456, "novo_lead")
    ]
    funil = web.get("/oportunidades").text
    assert "Projeto ficticio" in funil and "R$ 1.234,56" in funil


@pytest.mark.parametrize(
    ("campos", "campo", "mensagem"),
    [
        ({"valor_centavos": "1,234.56"}, "valor_centavos", "Use o formato 1.234,56"),
        ({"titulo": " "}, "titulo", "Preencha este campo"),
        ({"previsao_fechamento": "31/12/2026"}, "previsao_fechamento", "Data inválida"),
    ],
)
def test_invalid_form_returns_422_on_the_field_without_saving(
    web: TestClient, db: Path, campos: dict[str, str], campo: str, mensagem: str
) -> None:
    cliente_id = _cliente(web)
    dados = {"cliente_id": str(cliente_id), "titulo": "Projeto", "valor_centavos": ""}
    resposta = _post(web, "/oportunidades", **(dados | campos))
    assert resposta.status_code == 422
    assert f'id="erro-{campo}"' in resposta.text and mensagem in resposta.text
    assert _consulta(db, "SELECT count(*) FROM oportunidades") == [(0,)]


def test_create_for_missing_or_invalid_client_is_404(web: TestClient) -> None:
    for cliente_id in ("999", "abc", ""):
        resposta = _post(web, "/oportunidades", cliente_id=cliente_id, titulo="X")
        assert resposta.status_code == 404, cliente_id
    assert web.get("/oportunidades/nova", params={"cliente_id": "999"}).status_code == 404


def test_stage_changes_through_the_form(web: TestClient, db: Path) -> None:
    oportunidade_id = _criar(web)
    url = f"/oportunidades/{oportunidade_id}/etapa"
    assert _post(web, url, etapa="negociacao").status_code == 303
    perder = _post(web, url, etapa="perdida")
    assert perder.status_code == 422 and "Escolha o motivo da perda" in perder.text
    assert _post(web, url, etapa="perdida", motivo_perda="preco").status_code == 303
    ganhar = _post(web, url, etapa="ganha")
    assert ganhar.status_code == 422 and "Reabra em uma etapa aberta" in ganhar.text
    assert _post(web, url, etapa="qualificacao").status_code == 303
    detalhe = web.get(f"/oportunidades/{oportunidade_id}").text
    assert "Venda perdida" in detalhe and "Qualificação" in detalhe
    assert _consulta(db, "SELECT count(*) FROM movimentacoes") == [(4,)]


def test_win_without_value_is_refused_on_the_stage_field(web: TestClient) -> None:
    oportunidade_id = _criar(web, valor_centavos="")
    resposta = _post(web, f"/oportunidades/{oportunidade_id}/etapa", etapa="ganha")
    assert resposta.status_code == 422
    assert 'id="erro-etapa"' in resposta.text and "valor maior que zero" in resposta.text


def test_edit_changes_data_and_never_writes_history(web: TestClient, db: Path) -> None:
    oportunidade_id = _criar(web)
    resposta = _post(
        web,
        f"/oportunidades/{oportunidade_id}",
        titulo="Outro",
        valor_centavos="10",
        observacoes="Nota",
    )
    assert resposta.status_code == 303
    assert _consulta(db, "SELECT titulo, valor_centavos, observacoes FROM oportunidades") == [
        ("Outro", 1000, "Nota")
    ]
    assert _consulta(db, "SELECT count(*) FROM movimentacoes") == [(1,)]
    assert "Outro" in web.get(f"/oportunidades/{oportunidade_id}/editar").text


def test_text_is_escaped_everywhere(web: TestClient) -> None:
    cliente_id = _cliente(web)
    oportunidade_id = _criar(web, cliente_id, titulo=XSS, observacoes=XSS)
    for url in (
        "/oportunidades",
        "/oportunidades/lista",
        f"/oportunidades/{oportunidade_id}",
        f"/clientes/{cliente_id}",
        f"/oportunidades/{oportunidade_id}/editar",
    ):
        texto = web.get(url).text
        assert XSS not in texto, url
        assert "&lt;script&gt;" in texto, url


@pytest.mark.parametrize(
    ("params", "mensagem"),
    [
        ({"de": "2026-10-02", "ate": "2026-10-01"}, "A data final é anterior à inicial"),
        ({"de": "2026-02-30"}, "Data inválida"),
        ({"situacao": "contratos"}, "Valor inválido"),
    ],
)
def test_invalid_filters_return_422_with_message(
    web: TestClient, params: dict[str, str], mensagem: str
) -> None:
    for url in ("/oportunidades", "/oportunidades/lista"):
        resposta = web.get(url, params=params)
        assert resposta.status_code == 422, url
        assert mensagem in resposta.text, url


def test_list_paginates_and_filters_by_stage(web: TestClient) -> None:
    cliente_id = _cliente(web)
    for i in range(21):
        _criar(web, cliente_id, titulo=f"Op {i:02d}")
    primeira = web.get("/oportunidades/lista").text
    assert primeira.count('class="oportunidade"') == 20
    assert "pagina=2" in primeira
    assert (
        web.get("/oportunidades/lista", params={"pagina": 2}).text.count('class="oportunidade"')
        == 1
    )
    assert (
        'class="oportunidade"'
        not in web.get("/oportunidades/lista", params={"etapa": "ganha"}).text
    )
    assert web.get("/oportunidades/lista", params={"etapa": "contrato"}).status_code == 422
    assert web.get("/oportunidades/lista", params={"pagina": "0"}).status_code == 422


def test_client_page_lists_opportunities_and_link_to_create(web: TestClient) -> None:
    cliente_id = _cliente(web)
    _criar(web, cliente_id, titulo="Projeto do cliente")
    texto = web.get(f"/clientes/{cliente_id}").text
    assert "Projeto do cliente" in texto
    assert f'href="/oportunidades/nova?cliente_id={cliente_id}"' in texto
    assert "Oportunidade #1 criada" in texto  # evento na linha do tempo, sem o título
    nova = web.get("/oportunidades/nova", params={"cliente_id": cliente_id})
    assert nova.status_code == 200 and f'value="{cliente_id}"' in nova.text


def test_missing_opportunity_is_404_and_anonymized_client_is_409(web: TestClient) -> None:
    for url in ("/oportunidades/999", "/oportunidades/999/editar"):
        assert web.get(url).status_code == 404
    assert _post(web, "/oportunidades/999/etapa", etapa="negociacao").status_code == 404
    cliente_id = _cliente(web)
    oportunidade_id = _criar(web, cliente_id)
    _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id))
    tentativas = [
        ("/oportunidades", {"cliente_id": str(cliente_id), "titulo": "X"}),
        (f"/oportunidades/{oportunidade_id}", {"titulo": "X"}),
        (f"/oportunidades/{oportunidade_id}/etapa", {"etapa": "negociacao"}),
    ]
    for url, dados in tentativas:
        resposta = _post(web, url, **dados)
        assert resposta.status_code == 409, url
        assert "Projeto ficticio" not in resposta.text
    assert web.get(f"/oportunidades/{oportunidade_id}/editar").status_code == 409
    assert web.get("/oportunidades/nova", params={"cliente_id": cliente_id}).status_code == 409


def _rotas(rotas: Sequence[BaseRoute]) -> Iterator[APIRoute]:
    for rota in rotas:
        if isinstance(rota, APIRoute):
            yield rota
        elif incluido := getattr(rota, "original_router", None):
            yield from _rotas(incluido.routes)


def _urls(app: FastAPI, metodo: str, oportunidade_id: int) -> list[str]:
    return [
        r.path.replace("{oportunidade_id}", str(oportunidade_id))
        for r in _rotas(app.routes)
        if r.path.startswith("/oportunidades") and metodo in (r.methods or set())
    ]


def test_every_opportunity_post_requires_csrf_and_gets_change_nothing(
    web: TestClient, web_app: FastAPI, db: Path
) -> None:
    cliente_id = _cliente(web)
    oportunidade_id = _criar(web, cliente_id)
    posts = _urls(web_app, "POST", oportunidade_id)
    assert sorted(posts) == sorted(
        [
            "/oportunidades",
            f"/oportunidades/{oportunidade_id}",
            f"/oportunidades/{oportunidade_id}/etapa",
        ]
    )
    antes = _dump(db)
    for url in posts:
        dados = {"cliente_id": str(cliente_id), "titulo": "Invasor", "etapa": "negociacao"}
        assert web.post(url, data=dados).status_code == 403, url
        assert web.post(url, data={CSRF_FIELD: "falso", **dados}).status_code == 403, url
    for url in _urls(web_app, "GET", oportunidade_id):
        assert web.get(url, params={"cliente_id": cliente_id}).status_code == 200, url
    assert _dump(db) == antes  # banco inteiro, inclusive os eventos em interacoes
    escritores = [r.path for r in _rotas(web_app.routes) if r.methods == {"POST"}]
    assert [p for p in escritores if "etapa" in p or "moviment" in p] == [
        "/oportunidades/{oportunidade_id}/etapa"
    ]


@pytest.mark.parametrize("ident", ["99999999999999999999", "0", "-1"])
def test_out_of_range_ids_are_refused_without_server_error(web: TestClient, ident: str) -> None:
    for url in (f"/oportunidades/{ident}", f"/oportunidades/{ident}/editar"):
        assert web.get(url).status_code in (404, 422), url
    for url in (f"/oportunidades/{ident}", f"/oportunidades/{ident}/etapa"):
        assert _post(web, url, titulo="X", etapa="negociacao").status_code in (404, 422), url
