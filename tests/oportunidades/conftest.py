import sys
import time
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as s:
        yield s


@pytest.fixture
def fuso(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fixa o fuso do processo em America/Sao_Paulo (só POSIX: o Windows não tem tzset)."""
    if sys.platform == "win32" or not hasattr(time, "tzset"):
        pytest.skip("time.tzset só existe em POSIX; fuso histórico não verificado no Windows")
    monkeypatch.setenv("TZ", "America/Sao_Paulo")
    time.tzset()
    yield
    monkeypatch.undo()  # devolve o TZ original antes de recarregar o fuso
    time.tzset()
