import shutil
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
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
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003"

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
down_revision = "{head}"


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
    # Encadeia no head atual, para o teste continuar válido a cada nova migração.
    head = ScriptDirectory(str(scripts)).get_current_head()
    orphan = ORPHAN_MIGRATION.replace("{head}", str(head))
    (scripts / "versions" / "9001_orfao.py").write_text(orphan, encoding="utf-8")
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
    # Toda a execução do upgrade é uma transação só (transactional_ddl): nada fica aplicado.
    assert version is None


def test_0002_downgrade_to_0001_removes_only_phase_02_tables(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'fase02.db'}"
    config = _alembic_config(db_url)
    command.upgrade(config, "head")
    command.downgrade(config, "0001")
    engine = create_db_engine(db_url)
    with engine.connect() as conn:
        assert set(inspect(conn).get_table_names()) == {"alembic_version"}
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
    engine.dispose()
    command.upgrade(config, "head")


def test_0003_downgrade_keeps_phase_02_data_and_upgrades_again(tmp_path: Path) -> None:
    """upgrade → downgrade → upgrade da 0003, só em banco temporário, sem perder clientes."""
    db_url = f"sqlite:///{tmp_path / 'fase03.db'}"
    config = _alembic_config(db_url)
    engine = create_db_engine(db_url)
    command.upgrade(config, "0002")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO clientes (tipo, nome, origem) "
                "VALUES ('PJ', 'Cliente Ficticio', 'site')"
            )
        )
    command.upgrade(config, "head")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO oportunidades (cliente_id, titulo, etapa) "
                "VALUES (1, 'Projeto ficticio', 'novo_lead')"
            )
        )
    command.downgrade(config, "0002")
    with engine.connect() as conn:
        tabelas = set(inspect(conn).get_table_names())
        assert "oportunidades" not in tabelas and "movimentacoes" not in tabelas
        assert {"clientes", "contatos", "interacoes"} <= tabelas
        assert conn.execute(text("SELECT nome FROM clientes")).scalar_one() == "Cliente Ficticio"
    command.upgrade(config, "head")
    command.check(config)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM oportunidades")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM clientes")).scalar_one() == 1
    engine.dispose()
