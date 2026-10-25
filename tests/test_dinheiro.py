"""Dinheiro em centavos inteiros (R8): só formatos pt-BR, sem float nem arredondamento."""

import pytest

from salesos.dinheiro import MAXIMO_CENTAVOS, centavos, reais


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1.234,56", 123456),
        ("1234,56", 123456),
        ("1234", 123400),
        ("0,5", 50),
        ("0,05", 5),
        ("0", 0),
        (" 12 ", 1200),
        ("1.000", 100000),
        ("10.000.000.000,00", 10**12),
    ],
)
def test_accepted_formats(texto: str, esperado: int) -> None:
    assert centavos(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "-10",
        "+10",
        "1e3",
        "1,234.56",
        "1.234.56",
        "1234.56",
        "0,001",
        "",
        "   ",
        "12,3,4",
        "1.23,00",
        "12.3456",
        ",5",
        "12,",
        "R$ 10",
        "1 234",
        "١٢",
        "nan",
        "10.000.000.000,01",
    ],
)
def test_rejected_formats(texto: str) -> None:
    with pytest.raises(ValueError, match="Valor inválido"):
        centavos(texto)


def test_limit_is_one_trillion_cents() -> None:
    assert MAXIMO_CENTAVOS == 10**12


@pytest.mark.parametrize(
    ("valor", "texto"),
    [
        (123456, "R$ 1.234,56"),
        (0, "R$ 0,00"),
        (5, "R$ 0,05"),
        (100000, "R$ 1.000,00"),
        (10**12, "R$ 10.000.000.000,00"),
    ],
)
def test_format_in_reais(valor: int, texto: str) -> None:
    assert reais(valor) == texto


@pytest.mark.parametrize("valor", [0, 5, 99, 123456, 10**12])
def test_round_trip(valor: int) -> None:
    assert centavos(reais(valor).removeprefix("R$ ")) == valor


def test_negative_amount_cannot_be_formatted() -> None:
    with pytest.raises(ValueError):
        reais(-1)


@pytest.mark.parametrize("texto", ["9" * 5000, "9" * 14, "0" * 30 + "1"])
def test_too_many_digits_is_rejected_before_conversion(texto: str) -> None:
    """Sem isso, `int()` de milhares de dígitos falha com outra mensagem (ou gasta CPU)."""
    with pytest.raises(ValueError, match="Valor inválido"):
        centavos(texto)


@pytest.mark.parametrize("texto", ["0012", "01.234", "00.000", "00", "00,50"])
def test_leading_zeros_are_rejected(texto: str) -> None:
    with pytest.raises(ValueError, match="Valor inválido"):
        centavos(texto)


@pytest.mark.parametrize("valor", [True, 1.5, 10**12 + 1, 10**13, "100"])
def test_reais_only_formats_valid_amounts(valor: object) -> None:
    with pytest.raises(ValueError):
        reais(valor)  # type: ignore[arg-type]
