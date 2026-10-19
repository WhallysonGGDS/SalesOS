from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from salesos.db import check_foreign_keys, create_db_engine, foreign_keys_disabled


def test_sqlite_pragmas(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
    engine.dispose()


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'fk.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE pai (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text("CREATE TABLE filho (id INTEGER PRIMARY KEY, pai_id INTEGER REFERENCES pai(id))")
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("INSERT INTO filho (pai_id) VALUES (999)"))
    engine.dispose()


def test_missing_data_directory_is_created(tmp_path: Path) -> None:
    db_file = tmp_path / "ainda" / "nao" / "existe" / "salesos.db"
    engine = create_db_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    assert db_file.exists()
    engine.dispose()


def _parent_child_db(tmp_path: Path) -> Engine:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'migracao.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE pai (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE filho (id INTEGER PRIMARY KEY, "
                "pai_id INTEGER REFERENCES pai(id) ON DELETE CASCADE)"
            )
        )
        conn.execute(text("INSERT INTO pai (id) VALUES (1)"))
        conn.execute(text("INSERT INTO filho (pai_id) VALUES (1)"))
    return engine


def test_batch_migration_keeps_child_rows(tmp_path: Path) -> None:
    """SQLite recria a tabela em batch; com FK ligada o DROP apagaria os filhos em cascata."""
    engine = _parent_child_db(tmp_path)
    with engine.connect() as conn, foreign_keys_disabled(conn), conn.begin():
        ops = Operations(MigrationContext.configure(conn))
        with ops.batch_alter_table("pai", recreate="always") as batch:
            batch.add_column(sa.Column("nome", sa.String()))
        check_foreign_keys(conn)
    # A mesma conexão volta ao pool: FK precisa estar religada para o resto da aplicação.
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM filho")).scalar_one() == 1
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    engine.dispose()


def test_foreign_key_check_reports_orphans(tmp_path: Path) -> None:
    engine = _parent_child_db(tmp_path)
    with engine.connect() as conn, foreign_keys_disabled(conn), conn.begin():
        conn.execute(text("INSERT INTO filho (pai_id) VALUES (999)"))
        with pytest.raises(RuntimeError, match="chave estrangeira"):
            check_foreign_keys(conn)
    engine.dispose()


def test_foreign_keys_are_restored_after_failed_migration(tmp_path: Path) -> None:
    engine = _parent_child_db(tmp_path)
    with pytest.raises(RuntimeError), engine.connect() as conn, foreign_keys_disabled(conn):
        raise RuntimeError("falha simulada no meio da migração")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    engine.dispose()
