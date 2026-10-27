"""Rotas e telas das tarefas: CSRF, 303, 422 no campo, XSS, 404/409 e GET sem efeito."""

import logging
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from salesos.security import CSRF_FIELD
from tests.oportunidades.test_routes import XSS, _consulta, _dump, _post, _rotas
from tests.tarefas.conftest import FUTURO, PASSADO, _cliente, _oportunidade, _tarefa


def test_empty_agenda_invites_to_create_from_a_client(web: TestClient) -> None:
    resposta = web.get("/tarefas")
    assert resposta.status_code == 200
    assert "Nenhuma tarefa" in resposta.text
    assert 'href="/tarefas" aria-current="page"' in resposta.text
    assert "default-src 'self'" in resposta.headers["content-security-policy"]


@pytest.mark.usefixtures("fuso")
def test_create_reads_local_time_and_shows_detail(web: TestClient, db: Path) -> None:
    tarefa_id = _tarefa(web, prazo="2026-11-03T10:00", prioridade="alta", descricao="Pauta")
    assert _consulta(db, "SELECT prazo, estado, prioridade FROM tarefas") == [
        ("2026-11-03 13:00:00.000000", "pendente", "alta")
    ]
    detalhe = web.get(f"/tarefas/{tarefa_id}").text
    for texto in ("Ligar para o cliente", "Ligação", "Pendente", "Alta", "03/11/2026 10:00"):
        assert texto in detalhe, texto
    assert "Criada" in detalhe and "Pauta" in detalhe


@pytest.mark.parametrize(
    ("campos", "campo", "mensagem"),
    [
        ({"prazo": "amanhã"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": "1700000000"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": ""}, "prazo", "Informe data e hora válidas"),
        ({"titulo": " "}, "titulo", "Preencha este campo"),
        ({"tipo": "email"}, "tipo", "Valor inválido"),
        ({"oportunidade_id": "abc"}, "oportunidade_id", "Valor inválido"),
    ],
)
def test_invalid_form_returns_422_on_the_field_without_saving(
    web: TestClient, db: Path, campos: dict[str, str], campo: str, mensagem: str
) -> None:
    dados = {"cliente_id": str(_cliente(web)), "tipo": "ligacao", "titulo": "X", "prazo": FUTURO}
    resposta = _post(web, "/tarefas", **(dados | campos))
    assert resposta.status_code == 422
    assert f'id="erro-{campo}"' in resposta.text and mensagem in resposta.text
    assert _consulta(db, "SELECT count(*) FROM tarefas") == [(0,)]


def test_opportunity_of_another_client_is_refused_on_the_field(web: TestClient, db: Path) -> None:
    outra = _oportunidade(web, _cliente(web, "Outra Ficticia"))
    cliente_id = _cliente(web)
    dados = {"cliente_id": str(cliente_id), "tipo": "retorno", "titulo": "X", "prazo": FUTURO}
    resposta = _post(web, "/tarefas", oportunidade_id=str(outra), **dados)
    assert resposta.status_code == 422
    assert 'id="erro-oportunidade_id"' in resposta.text
    assert "Escolha uma oportunidade deste cliente" in resposta.text
    tarefa_id = _tarefa(web, cliente_id)
    editar = _post(web, f"/tarefas/{tarefa_id}", oportunidade_id=str(outra), **dados)
    assert editar.status_code == 422 and "Escolha uma oportunidade deste cliente" in editar.text
    assert _consulta(db, "SELECT oportunidade_id FROM tarefas") == [(None,)]


def test_create_for_missing_or_invalid_client_is_404(web: TestClient) -> None:
    for cliente_id in ("999", "abc", "", "99999999999999999999"):
        resposta = _post(web, "/tarefas", cliente_id=cliente_id, titulo="X")
        assert resposta.status_code == 404, cliente_id
    assert web.get("/tarefas/nova", params={"cliente_id": "999"}).status_code == 404


def test_state_changes_keep_history_and_closed_to_closed_needs_reopening(
    web: TestClient, db: Path
) -> None:
    tarefa_id = _tarefa(web)
    url = f"/tarefas/{tarefa_id}"
    assert _post(web, f"{url}/concluir").status_code == 303
    assert "Concluída" in web.get(url).text
    recusa = _post(web, f"{url}/cancelar")
    assert recusa.status_code == 422 and "Reabra a tarefa antes de mudar o estado" in recusa.text
    assert _post(web, f"{url}/reabrir").status_code == 303
    assert _post(web, f"{url}/cancelar").status_code == 303
    assert _post(web, f"{url}/cancelar").status_code == 303  # repetir não gera evento
    assert _consulta(db, "SELECT acao FROM tarefa_eventos ORDER BY id") == [
        ("criada",),
        ("concluida",),
        ("reaberta",),
        ("cancelada",),
    ]
    detalhe = web.get(url).text
    assert "Reabrir tarefa" in detalhe and "Reaberta" in detalhe


def test_edit_only_while_pending(web: TestClient, db: Path) -> None:
    tarefa_id = _tarefa(web)
    url = f"/tarefas/{tarefa_id}"
    assert 'value="2099-01-01T10:00"' in web.get(f"{url}/editar").text
    dados = {"tipo": "reuniao", "titulo": "Reunião ficticia", "prazo": FUTURO}
    assert _post(web, url, **dados).status_code == 303
    assert _consulta(db, "SELECT tipo, titulo FROM tarefas") == [("reuniao", "Reunião ficticia")]
    _post(web, f"{url}/concluir")
    assert web.get(f"{url}/editar").status_code == 409
    recusa = _post(web, url, **(dados | {"titulo": "Outro"}))
    assert recusa.status_code == 409 and "Reabra a tarefa antes" in recusa.text
    assert "Salvar alterações" not in recusa.text
    assert "Editar tarefa" not in web.get(url).text


def test_text_is_escaped_everywhere(web: TestClient) -> None:
    cliente_id = _cliente(web)
    oportunidade_id = _oportunidade(web, cliente_id)
    tarefa_id = _tarefa(
        web, cliente_id, titulo=XSS, descricao=XSS, oportunidade_id=str(oportunidade_id)
    )
    for url in (
        "/tarefas",
        f"/tarefas/{tarefa_id}",
        f"/tarefas/{tarefa_id}/editar",
        f"/clientes/{cliente_id}",
        f"/oportunidades/{oportunidade_id}",
    ):
        texto = web.get(url).text
        assert XSS not in texto, url
        assert "&lt;script&gt;" in texto, url


@pytest.mark.parametrize(
    ("params", "mensagem"),
    [
        ({"de": "2026-10-02", "ate": "2026-10-01"}, "A data final é anterior à inicial"),
        ({"de": "2026-02-30"}, "Data inválida"),
        ({"estado": "arquivada"}, "Valor inválido"),
        ({"tipo": "email"}, "Valor inválido"),
    ],
)
def test_invalid_filters_return_422_with_message(
    web: TestClient, params: dict[str, str], mensagem: str
) -> None:
    resposta = web.get("/tarefas", params=params)
    assert resposta.status_code == 422
    assert mensagem in resposta.text


def test_agenda_shows_overdue_first_and_the_counter_in_text(web: TestClient) -> None:
    cliente_id = _cliente(web)
    _tarefa(web, cliente_id, titulo="Atrasada ficticia", prazo=PASSADO)
    _tarefa(web, cliente_id, titulo="Futura ficticia")
    concluida = _tarefa(web, cliente_id, titulo="Concluida ficticia", prazo=PASSADO)
    _post(web, f"/tarefas/{concluida}/concluir")
    agenda = web.get("/tarefas").text
    vencidas, _, resto = agenda.partition('id="titulo-proximas"')
    assert "Atrasada ficticia" in vencidas and ">Vencida</strong>" in vencidas
    # Quem navega pelos links ouve também "Vencida": a linha de apoio descreve o link.
    assert 'aria-describedby="tarefa-meta-1"' in vencidas and 'id="tarefa-meta-1"' in vencidas
    assert "Atrasada ficticia" not in resto and ">Vencida</strong>" not in resto
    assert "Futura ficticia" in resto and "Concluida ficticia" not in agenda
    # Em texto, não só um ponto colorido; aparece em qualquer página.
    assert "1 vencida" in web.get("/clientes").text
    _tarefa(web, cliente_id, prazo=PASSADO)
    assert "2 vencidas" in web.get(f"/clientes/{cliente_id}").text
    assert "Concluida ficticia" in web.get("/tarefas", params={"estado": "concluida"}).text


def test_agenda_paginates_and_refuses_bad_pages(web: TestClient) -> None:
    cliente_id = _cliente(web)
    for i in range(21):
        _tarefa(web, cliente_id, titulo=f"Tarefa {i:02d}")
    primeira = web.get("/tarefas").text
    assert primeira.count('class="tarefa"') == 20 and "pagina=2" in primeira
    assert web.get("/tarefas", params={"pagina": 2}).text.count('class="tarefa"') == 1
    for pagina in ("0", "10000000000000000000"):
        assert web.get("/tarefas", params={"pagina": pagina}).status_code == 422


def test_client_and_opportunity_pages_list_tasks_and_link_to_create(web: TestClient) -> None:
    cliente_id = _cliente(web)
    oportunidade_id = _oportunidade(web, cliente_id)
    _tarefa(web, cliente_id, titulo="Tarefa do cliente", oportunidade_id=str(oportunidade_id))
    cliente = web.get(f"/clientes/{cliente_id}").text
    assert "Tarefa do cliente" in cliente
    assert f'href="/tarefas/nova?cliente_id={cliente_id}"' in cliente
    assert "Tarefa #1 criada" in cliente  # evento na linha do tempo, sem o título
    oportunidade = web.get(f"/oportunidades/{oportunidade_id}").text
    assert "Tarefa do cliente" in oportunidade
    link = f"/tarefas/nova?cliente_id={cliente_id}&amp;oportunidade_id={oportunidade_id}"
    assert f'href="{link}"' in oportunidade
    nova = web.get(
        "/tarefas/nova", params={"cliente_id": cliente_id, "oportunidade_id": oportunidade_id}
    )
    assert nova.status_code == 200
    assert f'<option value="{oportunidade_id}" selected>' in nova.text
    alheia = {"cliente_id": _cliente(web, "Outra Ficticia"), "oportunidade_id": oportunidade_id}
    assert web.get("/tarefas/nova", params=alheia).status_code == 404


def test_missing_task_is_404_and_anonymized_client_is_409(web: TestClient) -> None:
    for url in ("/tarefas/999", "/tarefas/999/editar"):
        assert web.get(url).status_code == 404
    for acao in ("", "/concluir", "/cancelar", "/reabrir"):
        assert _post(web, f"/tarefas/999{acao}", titulo="X").status_code == 404
    cliente_id = _cliente(web)
    tarefa_id = _tarefa(web, cliente_id, titulo="Segredo ficticio")
    _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id))
    tentativas = [
        ("/tarefas", {"cliente_id": str(cliente_id), "titulo": "X"}),
        (f"/tarefas/{tarefa_id}", {"titulo": "X"}),
        (f"/tarefas/{tarefa_id}/concluir", {}),
        (f"/tarefas/{tarefa_id}/cancelar", {}),
        (f"/tarefas/{tarefa_id}/reabrir", {}),
    ]
    for url, dados in tentativas:
        resposta = _post(web, url, **dados)
        assert resposta.status_code == 409, url
        assert "Este cliente foi anonimizado" in resposta.text, url  # página genérica, sem dados
    assert web.get(f"/tarefas/{tarefa_id}/editar").status_code == 409
    assert web.get("/tarefas/nova", params={"cliente_id": cliente_id}).status_code == 409
    assert f"Tarefa #{tarefa_id}" in web.get(f"/tarefas/{tarefa_id}").text


def _urls(app: FastAPI, metodo: str, tarefa_id: int) -> list[str]:
    return [
        r.path.replace("{tarefa_id}", str(tarefa_id))
        for r in _rotas(app.routes)
        if r.path.startswith("/tarefas") and metodo in (r.methods or set())
    ]


def test_every_task_post_requires_csrf_and_gets_change_nothing(
    web: TestClient, web_app: FastAPI, db: Path
) -> None:
    cliente_id = _cliente(web)
    tarefa_id = _tarefa(web, cliente_id, prazo=PASSADO)
    posts = _urls(web_app, "POST", tarefa_id)
    base = f"/tarefas/{tarefa_id}"
    assert sorted(posts) == sorted(
        ["/tarefas", base, f"{base}/concluir", f"{base}/cancelar", f"{base}/reabrir"]
    )
    antes = _dump(db)
    for url in posts:
        dados = {"cliente_id": str(cliente_id), "titulo": "Invasor", "tipo": "ligacao"}
        assert web.post(url, data=dados).status_code == 403, url
        assert web.post(url, data={CSRF_FIELD: "falso", **dados}).status_code == 403, url
    for url in _urls(web_app, "GET", tarefa_id):
        assert web.get(url, params={"cliente_id": cliente_id}).status_code == 200, url
    assert _dump(db) == antes  # banco inteiro, inclusive o histórico e os eventos do cliente


@pytest.mark.parametrize("ident", ["99999999999999999999", "0", "-1"])
def test_out_of_range_ids_are_refused_without_server_error(web: TestClient, ident: str) -> None:
    for url in (f"/tarefas/{ident}", f"/tarefas/{ident}/editar"):
        assert web.get(url).status_code in (404, 422), url
    for acao in ("", "/concluir", "/cancelar", "/reabrir"):
        assert _post(web, f"/tarefas/{ident}{acao}", titulo="X").status_code in (404, 422), acao
    for params in ({"cliente_id": "1", "oportunidade_id": ident}, {"cliente_id": ident}):
        assert web.get("/tarefas/nova", params=params).status_code in (404, 422), params


def test_home_still_renders_before_migrations(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    resposta = client.get("/")
    assert resposta.status_code == 200 and "vencida" not in resposta.text
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]  # sem tabela: silêncio


def test_client_and_opportunity_pages_warn_about_overdue_tasks(web: TestClient) -> None:
    # D7: aviso na página do cliente e da oportunidade, em texto.
    cliente_id = _cliente(web)
    oportunidade_id = _oportunidade(web, cliente_id)
    _tarefa(web, cliente_id, prazo=PASSADO, oportunidade_id=str(oportunidade_id))
    assert "1 tarefa vencida" in web.get(f"/clientes/{cliente_id}").text
    assert "1 tarefa vencida" in web.get(f"/oportunidades/{oportunidade_id}").text
    _tarefa(web, cliente_id, prazo=PASSADO)
    assert "2 tarefas vencidas" in web.get(f"/clientes/{cliente_id}").text


def test_anonymized_client_tasks_are_not_shown_as_overdue(web: TestClient) -> None:
    # Ninguém consegue fechá-las (409): "Vencida" para sempre só confundiria.
    cliente_id = _cliente(web)
    tarefa_id = _tarefa(web, cliente_id, prazo=PASSADO)
    _post(web, f"/clientes/{cliente_id}/anonimizar", confirmacao=str(cliente_id))
    for url in (f"/clientes/{cliente_id}", f"/tarefas/{tarefa_id}"):
        texto = web.get(url).text
        assert "Vencida" not in texto and "tarefa vencida" not in texto, url
    assert "Pendente" in web.get(f"/tarefas/{tarefa_id}").text


def test_submitting_the_default_filters_is_the_plain_agenda(web: TestClient) -> None:
    padrao = web.get("/tarefas", params={"estado": "pendente", "tipo": "", "de": ""}).text
    assert "Limpar filtros" not in padrao and '<details class="filtros-caixa">' in padrao
    assert '<h1 class="titulo">Tarefas</h1>' in padrao
