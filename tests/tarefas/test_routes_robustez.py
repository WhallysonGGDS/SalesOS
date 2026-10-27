"""Rotas das tarefas diante de entradas extremas e de falhas do banco (revisão da etapa 4)."""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.backup.conftest import escutar
from tests.oportunidades.test_routes import _post
from tests.tarefas.conftest import _cliente, _oportunidade, _tarefa


@pytest.mark.parametrize("valor", ["0001-01-01T00:00+05:00", "9999-12-31T23:59-05:00"])
def test_dates_out_of_the_calendar_are_422_not_500(web: TestClient, valor: str) -> None:
    # Fora dos anos 1 a 9999 depois de converter o fuso, o Python lança OverflowError.
    cliente_id = _cliente(web)
    dados = {"cliente_id": str(cliente_id), "tipo": "ligacao", "titulo": "X", "prazo": valor}
    assert _post(web, "/tarefas", **dados).status_code == 422
    tarefa_id = _tarefa(web, cliente_id)
    assert _post(web, f"/tarefas/{tarefa_id}", **dados).status_code == 422
    interacao = {"tipo": "nota", "resumo": "X", "ocorrida_em": valor}
    assert _post(web, f"/clientes/{cliente_id}/interacoes", **interacao).status_code == 422


def test_editing_keeps_an_opportunity_older_than_the_listed_ones(web: TestClient, db: Path) -> None:
    cliente_id = _cliente(web)
    antiga = _oportunidade(web, cliente_id)
    for _ in range(50):  # a lista do formulário mostra só as 50 mais recentes
        _oportunidade(web, cliente_id)
    tarefa_id = _tarefa(web, cliente_id, oportunidade_id=str(antiga))
    assert f'<option value="{antiga}" selected>' in web.get(f"/tarefas/{tarefa_id}/editar").text
    nova = {"cliente_id": cliente_id, "oportunidade_id": antiga}
    assert f'<option value="{antiga}" selected>' in web.get("/tarefas/nova", params=nova).text


def test_counter_hides_only_a_missing_table_and_logs_other_errors(
    web: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from sqlalchemy.exc import OperationalError

    from salesos.features.tarefas import service

    def travado(*_a: object, **_k: object) -> int:
        raise OperationalError("SELECT", {}, Exception("database is locked"))

    escutar(caplog)
    monkeypatch.setattr(service, "contar_vencidas", travado)
    assert web.get("/clientes").status_code == 200
    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("contador de tarefas vencidas" in r.getMessage() for r in avisos)
