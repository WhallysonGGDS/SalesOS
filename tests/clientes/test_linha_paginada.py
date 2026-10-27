"""F: a linha do tempo é paginada; nenhuma interação antiga fica inacessível (E6)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salesos.db import create_db_engine
from salesos.features.clientes import service
from salesos.features.clientes.schemas import ClienteIn, InteracaoIn

INICIO = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _cliente_com_interacoes(session: Session, quantidade: int) -> int:
    cliente = service.criar_cliente(session, ClienteIn(tipo="PJ", nome="Ficticio", origem="site"))
    for n in range(quantidade):
        dados = InteracaoIn(
            tipo="nota", ocorrida_em=INICIO + timedelta(hours=n), resumo=f"nota {n:03d}"
        )
        service.registrar_interacao(session, cliente.id, dados)
    return cliente.id


@pytest.fixture
def client_web(web: TestClient, db: Path) -> Iterator[tuple[TestClient, int]]:
    """Cliente com 55 notas no mesmo banco que o cliente HTTP usa."""
    engine = create_db_engine(f"sqlite:///{db}")
    try:
        with Session(engine) as s:
            cliente_id = _cliente_com_interacoes(s, 55)
    finally:
        engine.dispose()
    yield web, cliente_id


def test_pages_cover_every_interaction_exactly_once(session: Session) -> None:
    cliente_id = _cliente_com_interacoes(session, 120)  # + 1 evento "Cliente criado"
    vistos: list[int] = []
    pagina = 1
    while pagina <= 10:  # teto: sem ele, uma paginação quebrada travaria o teste em vez de falhar
        resultado = service.listar_interacoes(session, cliente_id, pagina=pagina)
        assert len(resultado.itens) <= 50
        vistos += [i.id for i in resultado.itens]
        if not resultado.tem_proxima:
            break
        pagina += 1
    assert pagina == 3
    assert len(vistos) == len(set(vistos)) == 121  # nenhuma repetida, nenhuma perdida


def test_newest_first_and_the_oldest_is_on_the_last_page(session: Session) -> None:
    cliente_id = _cliente_com_interacoes(session, 60)
    primeira = service.listar_interacoes(session, cliente_id, pagina=1)
    ultima = service.listar_interacoes(session, cliente_id, pagina=2)
    notas = [i.resumo for i in primeira.itens if i.tipo == "nota"]  # "Cliente criado" é de hoje
    assert notas[0] == "nota 059" and primeira.tem_proxima
    assert ultima.itens[-1].resumo == "nota 000" and not ultima.tem_proxima


def test_client_page_links_to_older_and_newer_interactions(
    client_web: tuple[TestClient, int],
) -> None:
    web, cliente_id = client_web
    primeira = web.get(f"/clientes/{cliente_id}").text
    assert f'href="/clientes/{cliente_id}?linha_pagina=2#linha"' in primeira
    assert "Interações mais antigas" in primeira and "nota 054" in primeira
    segunda = web.get(f"/clientes/{cliente_id}", params={"linha_pagina": 2}).text
    assert "nota 000" in segunda and "nota 054" not in segunda
    assert f'href="/clientes/{cliente_id}?linha_pagina=1#linha"' in segunda
    assert "Interações mais antigas" not in segunda


@pytest.mark.parametrize("pagina", ["0", "-1", "100001", "abc", "99999999999999999999"])
def test_invalid_timeline_page_is_refused_without_server_error(
    client_web: tuple[TestClient, int], pagina: str
) -> None:
    web, cliente_id = client_web
    assert web.get(f"/clientes/{cliente_id}", params={"linha_pagina": pagina}).status_code == 422


def test_page_past_the_end_says_so_and_links_back(client_web: tuple[TestClient, int]) -> None:
    web, cliente_id = client_web
    texto = web.get(f"/clientes/{cliente_id}", params={"linha_pagina": 9}).text
    assert "Nenhuma interação registrada" not in texto
    assert "Nenhuma interação nesta página" in texto
    assert f'href="/clientes/{cliente_id}?linha_pagina=8#linha"' in texto
