"""Fixture `fuso` no Windows: só roda com o sistema no horário de Brasília (E4, P3)."""

from datetime import timedelta

import pytest

from tests.conftest import sistema_em_brasilia

TRES = timedelta(hours=-3)


@pytest.mark.parametrize(
    "nome",
    [
        "Hora oficial do Brasil",  # Windows em português
        "E. South America Standard Time",  # Windows em inglês
        "Brazil Standard Time",
    ],
)
def test_brasilia_is_recognized_by_name_and_current_offset(nome: str) -> None:
    assert sistema_em_brasilia(nome, TRES)


@pytest.mark.parametrize(
    ("nome", "deslocamento"),
    [
        ("Argentina Standard Time", TRES),  # mesmo deslocamento, outras regras históricas
        ("SA Eastern Standard Time", TRES),  # Caiena e Fortaleza: nunca tiveram o verão de SP
        ("Hora oficial do Brasil", timedelta(hours=-2)),  # nome certo, deslocamento estranho
        ("UTC", timedelta(0)),
    ],
)
def test_other_zones_are_not_taken_for_brasilia(nome: str, deslocamento: timedelta) -> None:
    assert not sistema_em_brasilia(nome, deslocamento)
