"""G: páginas HTML para 403, 413 e 422 quando quem pede é o navegador (E6).

Quem não pede HTML (APIs, scripts, `/health`) continua recebendo o formato de antes: JSON no
403 e no 422 (este sem o campo `input`), texto puro no 413. Nada do que foi enviado volta.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from salesos.config import Settings
from salesos.main import create_app
from salesos.security import LIMITE_CORPO
from tests.conftest import migrar

NAVEGADOR = {"accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
SENTINELA = "Qwxerrosentinela"


@pytest.fixture
def web(tmp_path: Path, settings: Settings) -> Iterator[TestClient]:
    migrar(tmp_path / "teste.db")
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as cliente:
        cliente.get("/clientes")  # cookie CSRF
        yield cliente


def _pagina(resposta: object) -> str:
    texto: str = resposta.text  # type: ignore[attr-defined]
    cabecalhos = resposta.headers  # type: ignore[attr-defined]
    assert cabecalhos["content-type"].startswith("text/html")
    assert "default-src 'self'" in cabecalhos["content-security-policy"]
    assert '<html lang="pt-BR">' in texto and "<h1" in texto
    assert SENTINELA not in texto  # nada do que foi enviado volta na página
    return texto


def test_csrf_refusal_is_a_page_for_the_browser(web: TestClient) -> None:
    resposta = web.post("/clientes", data={"nome": SENTINELA}, headers=NAVEGADOR)
    assert resposta.status_code == 403
    assert "Recarregue a página" in _pagina(resposta)


def test_csrf_refusal_stays_json_for_other_clients(web: TestClient) -> None:
    resposta = web.post("/clientes", data={"nome": SENTINELA})
    assert resposta.status_code == 403
    assert resposta.json() == {
        "detail": "Formulário expirado ou inválido. Recarregue a página e envie de novo."
    }


def test_invalid_address_is_a_page_for_the_browser(web: TestClient) -> None:
    resposta = web.get(f"/tarefas?pagina={SENTINELA}", headers=NAVEGADOR)
    assert resposta.status_code == 422
    assert "Endereço inválido" in _pagina(resposta)
    assert web.get("/tarefas/0", headers=NAVEGADOR).status_code == 422


def test_invalid_address_stays_json_for_other_clients(web: TestClient) -> None:
    resposta = web.get("/tarefas/0")
    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith("application/json")
    assert resposta.json()["detail"][0]["loc"] == ["path", "tarefa_id"]


def test_invalid_address_json_does_not_echo_the_sent_value(web: TestClient) -> None:
    resposta = web.get(f"/tarefas?pagina={SENTINELA}")
    assert resposta.status_code == 422
    assert SENTINELA not in resposta.text
    (erro,) = resposta.json()["detail"]
    assert erro["loc"] == ["query", "pagina"]
    assert erro["type"] == "int_parsing" and erro["msg"]


def test_too_large_is_a_page_for_the_browser(web: TestClient) -> None:
    corpo = {"nome": SENTINELA + "x" * (LIMITE_CORPO + 1)}
    resposta = web.post("/clientes", data=corpo, headers=NAVEGADOR)
    assert resposta.status_code == 413
    assert "grande demais" in _pagina(resposta)


def test_too_large_stays_plain_text_for_other_clients(web: TestClient) -> None:
    resposta = web.post("/clientes", data={"nome": "x" * (LIMITE_CORPO + 1)})
    assert resposta.status_code == 413
    assert resposta.headers["content-type"].startswith("text/plain")
    assert resposta.text == "Envio grande demais. Reduza o texto e tente de novo."


def test_health_is_untouched(web: TestClient) -> None:
    resposta = web.get("/health", headers=NAVEGADOR)
    assert resposta.json() == {"status": "ok", "database": "ok"}


def test_other_http_errors_keep_their_default_response(web: TestClient) -> None:
    # Só o 403 do CSRF ganhou página: um endereço inexistente continua com o 404 de sempre.
    resposta = web.get("/nao-existe", headers=NAVEGADOR)
    assert resposta.status_code == 404
    assert "Formulário expirado" not in resposta.text
