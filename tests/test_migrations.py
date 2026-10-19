import shutil
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from salesos.db import create_db_engine

ROOT = Path(__file__).resolve().parents[1]


def _alembic_config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_upgrade_check_and_downgrade(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'migracao.db'}"
    config = _alembic_config(db_url)
    engine = create_db_engine(db_url)

    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"

    # Sem diferenças entre os modelos e o banco migrado (levanta exceção se houver).
    command.check(config)

    command.downgrade(config, "base")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM alembic_version")).scalar_one() == 0
        assert set(inspect(conn).get_table_names()) == {"alembic_version"}
    engine.dispose()


ORPHAN_MIGRATION = '''"""Migração de teste que deixa um filho órfão."""

import sqlalchemy as sa
from alembic import op

revision = "9001"
down_revision = "0001"


def upgrade() -> None:
    op.create_table("pai", sa.Column("id", sa.Integer, primary_key=True))
    op.create_table(
        "filho",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pai_id", sa.Integer, sa.ForeignKey("pai.id")),
    )
    op.execute("INSERT INTO filho (pai_id) VALUES (999)")


def downgrade() -> None:
    op.drop_table("filho")
    op.drop_table("pai")
'''


def test_migration_with_foreign_key_violation_is_rolled_back(tmp_path: Path) -> None:
    """A checagem de FK precisa desfazer a migração inteira, não só avisar."""
    scripts = tmp_path / "migrations"
    shutil.copytree(ROOT / "migrations", scripts, ignore=shutil.ignore_patterns("__pycache__"))
    (scripts / "versions" / "9001_orfao.py").write_text(ORPHAN_MIGRATION, encoding="utf-8")
    db_url = f"sqlite:///{tmp_path / 'orfao.db'}"
    config = _alembic_config(db_url)
    config.set_main_option("script_location", str(scripts))

    with pytest.raises(RuntimeError, match="chave estrangeira"):
        command.upgrade(config, "head")

    engine = create_db_engine(db_url)
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    engine.dispose()
    assert "filho" not in tables
    assert "pai" not in tables
    assert version is None
