from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import Connection, Engine, MetaData, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session

# Nomes de constraints estáveis para que o Alembic gere migrações previsíveis.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",  # todas as colunas, unidas por "_"
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _apply_sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    # Zera o conteúdo apagado no arquivo (apoio à anonimização; não é garantia forense).
    cursor.execute("PRAGMA secure_delete=ON")
    cursor.close()


def sqlite_file(database_url: str) -> Path:
    """Caminho do arquivo SQLite; backup e restauração só existem para esse caso."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("backup e restauração exigem um banco SQLite em arquivo")
    return Path(url.database)


def create_db_engine(database_url: str) -> Engine:
    """Cria o engine; em SQLite cria a pasta do arquivo e ativa FK, WAL e busy_timeout."""
    url = make_url(database_url)
    # hide_parameters: erros e logs do SQLAlchemy não levam valores (dados pessoais).
    engine = create_engine(url, hide_parameters=True)
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


@contextmanager
def foreign_keys_disabled(connection: Connection) -> Iterator[None]:
    """Desliga FK nesta conexão durante uma migração e religa ao sair (mesmo com erro).

    Em batch, o SQLite recria a tabela (cria, copia, DROP e renomeia); com FK ligada, o DROP
    dispara ON DELETE CASCADE e apaga linhas filhas sem erro. O PRAGMA só vale fora de
    transação. A integridade deve ser conferida com check_foreign_keys antes do commit.
    """
    if connection.dialect.name != "sqlite":
        yield
        return
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    connection.commit()
    try:
        yield
    finally:
        if connection.in_transaction():
            connection.rollback()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()


def check_foreign_keys(connection: Connection) -> None:
    """Falha se alguma referência ficou órfã; no env.py, a exceção desfaz a migração inteira."""
    if connection.dialect.name != "sqlite":
        return
    violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(
            f"A migração deixou {len(violations)} violação(ões) de chave estrangeira"
        )


def get_session(request: Request) -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, sempre fechada no fim."""
    with Session(request.app.state.engine) as session:
        yield session
