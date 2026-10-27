from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as s:
        yield s
