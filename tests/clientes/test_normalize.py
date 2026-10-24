"""Normalização da Fase 02 (E1). CPF, CNPJ e telefone ficam fora até haver fonte oficial."""

import pytest

from salesos.features.clientes.normalize import like_contains, normalize_email, search_key


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("fulano@exemplo.com", "fulano@exemplo.com"),
        ("  Fulano.Tal@Exemplo.COM.br  ", "fulano.tal@exemplo.com.br"),
        ("contato+vendas@empresa-ficticia.dev", "contato+vendas@empresa-ficticia.dev"),
    ],
)
def test_normalize_email_trims_and_lowercases(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "semarroba.exemplo.com",
        "a@@exemplo.com",
        "a@b@exemplo.com",
        "@exemplo.com",
        "fulano@",
        "fulano@exemplo",
        "fulano@.exemplo.com",
        "fulano@exemplo.com.",
        "ful ano@exemplo.com",
        "fulano@exem plo.com",
        "x" * 245 + "@exemplo.com",
    ],
)
def test_normalize_email_rejects_invalid_structure(raw: str) -> None:
    with pytest.raises(ValueError, match="e-mail"):
        normalize_email(raw)


def test_search_key_removes_accents_case_and_extra_spaces() -> None:
    assert search_key("  José   da  Conceição ") == "jose da conceicao"


def test_search_key_joins_parts_and_skips_empty_ones() -> None:
    assert search_key("Ação Ltda", None, "", "VENDAS@Exemplo.com") == "acao ltda vendas@exemplo.com"


def test_search_key_uses_casefold() -> None:
    assert search_key("STRASSE", "Straße") == "strasse strasse"


def test_like_contains_escapes_wildcards_and_backslash() -> None:
    assert like_contains("50%_off\\x") == "%50\\%\\_off\\\\x%"


def test_like_contains_plain_term() -> None:
    assert like_contains("silva") == "%silva%"
