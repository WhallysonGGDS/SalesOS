"""Rotas de clientes: segurança transversal (CSRF, GET sem efeito, XSS, limite do corpo)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from salesos.features.clientes.schemas import TEXTO_LONGO_MAX
from salesos.security import CSRF_FIELD
from tests.clientes.test_routes import CLIENTE, XSS, _consulta, _criar, _dump, _post, _rotas

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
    # Rotas do funil precisam de ids de oportunidade: ver tests/oportunidades/test_routes.py.
    urls = [u for u in _urls(web_app, "GET", *com_dados) if not u.startswith("/oportunidades")]
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
