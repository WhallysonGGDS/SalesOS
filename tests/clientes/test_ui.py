"""Semântica e acessibilidade das telas (E6), lidas do HTML real com o parser da stdlib."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.clientes.test_routes import _consulta, _criar, _post

CAMPOS = ("input", "select", "textarea")


class _Arvore(HTMLParser):
    """Coleta elementos com atributos e o texto de cada `<label>` e `<button>`."""

    def __init__(self) -> None:
        super().__init__()
        self.elementos: list[tuple[str, dict[str, str]]] = []
        self.textos: dict[int, str] = {}
        self._abertos: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elementos.append((tag, {k: v or "" for k, v in attrs}))
        if tag in ("label", "button", "a"):
            self._abertos.append(len(self.elementos) - 1)
            self.textos[len(self.elementos) - 1] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag in ("label", "button", "a") and self._abertos:
            self._abertos.pop()

    def handle_data(self, data: str) -> None:
        for indice in self._abertos:
            self.textos[indice] += data

    def todos(self, tag: str) -> list[dict[str, str]]:
        return [a for t, a in self.elementos if t == tag]

    def texto(self, tag: str) -> list[str]:
        return [
            " ".join(self.textos[i].split()) for i, (t, _a) in enumerate(self.elementos) if t == tag
        ]


def _ler(html: str) -> _Arvore:
    arvore = _Arvore()
    arvore.feed(html)
    return arvore


@pytest.fixture
def paginas(web: TestClient, db: Path) -> dict[str, str]:
    cliente_id = _criar(web, nome="Empresa Ficticia", email="a@exemplo.com")
    _post(web, f"/clientes/{cliente_id}/contatos", nome="Pessoa Ficticia")
    ((contato_id,),) = _consulta(db, "SELECT id FROM contatos")
    urls = {
        "inicio": "/",
        "lista": "/clientes",
        "novo": "/clientes/novo",
        "detalhe": f"/clientes/{cliente_id}",
        "editar": f"/clientes/{cliente_id}/editar",
        "contato": f"/contatos/{contato_id}/editar",
    }
    return {nome: web.get(url).text for nome, url in urls.items()}


def test_every_form_control_has_a_label_and_unique_id(paginas: dict[str, str]) -> None:
    for nome, html in paginas.items():
        arvore = _ler(html)
        controles = [a for t, a in arvore.elementos if t in CAMPOS and a.get("type") != "hidden"]
        ids = [a.get("id", "") for t, a in arvore.elementos if a.get("id")]
        rotulados = {a["for"] for a in arvore.todos("label") if "for" in a}
        assert len(ids) == len(set(ids)), nome
        for controle in controles:
            assert controle.get("id") in rotulados, (nome, controle)


def test_every_page_has_one_h1_main_landmark_and_language(paginas: dict[str, str]) -> None:
    for nome, html in paginas.items():
        arvore = _ler(html)
        assert len(arvore.todos("h1")) == 1, nome
        assert len(arvore.todos("main")) == 1, nome
        assert arvore.todos("html")[0]["lang"] == "pt-BR"


def test_buttons_and_links_have_distinct_accessible_names(
    paginas: dict[str, str], web: TestClient, db: Path
) -> None:
    ((cliente_id,),) = _consulta(db, "SELECT id FROM clientes")
    _post(web, f"/clientes/{cliente_id}/contatos", nome="Outra Pessoa")
    arvore = _ler(web.get(f"/clientes/{cliente_id}").text)
    botoes = arvore.texto("button")
    assert "Remover contato Pessoa Ficticia" in botoes
    assert "Remover contato Outra Pessoa" in botoes
    assert "Editar contato Pessoa Ficticia" in arvore.texto("a")
    assert all(texto for texto in botoes)


def test_current_section_is_marked_in_navigation(paginas: dict[str, str]) -> None:
    for nome in ("lista", "novo", "detalhe", "editar", "contato"):
        links = _ler(paginas[nome]).todos("a")
        atuais = [a for a in links if a.get("aria-current") == "page"]
        assert [a["href"] for a in atuais] == ["/clientes"], nome
    assert not [a for a in _ler(paginas["inicio"]).todos("a") if a.get("aria-current")]


def test_home_page_describes_what_exists_now(paginas: dict[str, str]) -> None:
    inicio = paginas["inicio"]
    assert "Clientes, funil, tarefas e propostas chegam" not in inicio
    assert 'href="/clientes"' in inicio
    assert "Abrir clientes" in inicio


def test_empty_states_offer_the_next_step(web: TestClient) -> None:
    vazio = _ler(web.get("/clientes").text)
    assert ("/clientes/novo", "Cadastrar o primeiro cliente") in zip(
        [a.get("href") for a in vazio.todos("a")], vazio.texto("a"), strict=True
    )
    _criar(web, nome="Alguma Empresa")
    sem_resultado = _ler(web.get("/clientes", params={"q": "inexistente"}).text)
    assert ("/clientes", "Limpar busca") in zip(
        [a.get("href") for a in sem_resultado.todos("a")], sem_resultado.texto("a"), strict=True
    )


def test_timeline_dates_are_machine_readable(web: TestClient) -> None:
    cliente_id = _criar(web)
    tempos = _ler(web.get(f"/clientes/{cliente_id}").text).todos("time")
    assert tempos
    assert all(t.get("datetime", "").endswith("Z") for t in tempos)


def test_field_errors_are_linked_to_their_inputs(web: TestClient) -> None:
    arvore = _ler(_post(web, "/clientes", tipo="PJ", nome="", origem="site").text)
    invalidos = [a for t, a in arvore.elementos if a.get("aria-invalid") == "true"]
    ids = {a.get("id") for _t, a in arvore.elementos}
    assert invalidos
    for campo in invalidos:
        descritores = campo["aria-describedby"].split()
        assert descritores and all(d in ids for d in descritores)
