"""Período do calendário local → intervalo UTC (R7, decisão P3 do ADR 0006)."""

import zoneinfo
from datetime import UTC, date, datetime

import pytest

from salesos.features.oportunidades.periodo import intervalo_utc

SP = "America/Sao_Paulo"


def _utc(ano: int, mes: int, dia: int, hora: int = 0) -> datetime:
    return datetime(ano, mes, dia, hora, tzinfo=UTC)


@pytest.mark.usefixtures("fuso")
def test_both_limits_include_whole_local_days() -> None:
    inicio, fim = intervalo_utc(date(2026, 10, 1), date(2026, 10, 31))
    assert inicio == _utc(2026, 10, 1, 3)  # meia-noite em -03:00
    assert fim == _utc(2026, 11, 1, 3)  # exclusivo: o dia 31 entra inteiro


@pytest.mark.usefixtures("fuso")
def test_single_limits() -> None:
    assert intervalo_utc(date(2026, 10, 1), None) == (_utc(2026, 10, 1, 3), None)
    assert intervalo_utc(None, date(2026, 10, 1)) == (None, _utc(2026, 10, 2, 3))
    assert intervalo_utc(None, None) == (None, None)


def test_inverted_interval_is_refused() -> None:
    with pytest.raises(ValueError, match="anterior"):
        intervalo_utc(date(2026, 10, 2), date(2026, 10, 1))


def test_same_day_is_one_whole_day() -> None:
    inicio, fim = intervalo_utc(date(2026, 10, 1), date(2026, 10, 1))
    assert inicio is not None and fim is not None
    assert (fim - inicio).total_seconds() == 24 * 3600


@pytest.mark.usefixtures("fuso")
@pytest.mark.parametrize(
    ("dia", "esperado"),
    [
        # 2018-11-04: início do horário de verão à meia-noite; o dia começa às 01:00 (-02:00).
        (date(2018, 11, 4), _utc(2018, 11, 4, 3)),
        (date(2018, 12, 1), _utc(2018, 12, 1, 2)),  # em horário de verão (-02:00)
        (date(2019, 2, 16), _utc(2019, 2, 16, 2)),  # último dia do horário de verão
        (date(2019, 2, 17), _utc(2019, 2, 17, 3)),  # de volta a -03:00
        (date(2026, 1, 1), _utc(2026, 1, 1, 3)),  # sem horário de verão desde 2019
    ],
)
def test_historical_daylight_saving_uses_the_rules_of_that_date(
    dia: date, esperado: datetime
) -> None:
    inicio, _fim = intervalo_utc(dia, None)
    assert inicio == esperado
    # Confere contra a base IANA quando ela existe (Linux); no Windows não há tzdata.
    try:
        referencia = datetime(dia.year, dia.month, dia.day, tzinfo=zoneinfo.ZoneInfo(SP))
    except zoneinfo.ZoneInfoNotFoundError:
        return
    assert inicio == referencia.astimezone(UTC)


@pytest.mark.usefixtures("fuso")
def test_end_of_daylight_saving_day_has_25_hours() -> None:
    inicio, fim = intervalo_utc(date(2019, 2, 16), date(2019, 2, 16))
    assert inicio is not None and fim is not None
    assert (fim - inicio).total_seconds() == 25 * 3600
