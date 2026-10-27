"""Dias do calendário local → intervalo UTC `[início de de, início de ate+1)` (R7, ADR 0006).

A meia-noite local ingênua com `.astimezone(UTC)` aplica as regras de fuso do sistema
operacional para aquela data (horário de verão histórico incluído), não o offset de hoje.
Verificado no Linux; no Windows depende das regras do sistema e não está verificado (P3).
"""

import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from salesos.formularios import Mensagem


def _inicio_do_dia(dia: date) -> datetime:
    return datetime.combine(dia, time()).astimezone(UTC)


def intervalo_utc(de: date | None, ate: date | None) -> tuple[datetime | None, datetime | None]:
    if de is not None and ate is not None and ate < de:
        raise ValueError("A data final é anterior à inicial")
    inicio = None if de is None else _inicio_do_dia(de)
    fim = None if ate is None else _inicio_do_dia(ate + timedelta(days=1))
    return inicio, fim


_DATA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")  # o que o <input type="date"> envia


def data_do_formulario(value: Any) -> Any:
    """Só AAAA-MM-DD de 2000 a 2100; o Pydantic aceitaria timestamps e outros formatos."""
    if isinstance(value, str) and not value.strip():
        return None
    if value is None or isinstance(value, date):
        return value
    try:
        if isinstance(value, str) and _DATA.fullmatch(value):
            dia = date.fromisoformat(value)
            if 2000 <= dia.year <= 2100:
                return dia
    except ValueError:
        pass
    raise Mensagem("Data inválida")
