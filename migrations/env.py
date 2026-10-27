from contextlib import nullcontext
from logging.config import fileConfig
from pathlib import Path

from alembic import context

from salesos.config import Settings
from salesos.db import (
    Base,
    check_foreign_keys,
    create_db_engine,
    foreign_keys_disabled,
    sqlite_file,
)
from salesos.features.clientes import models as _clientes_models  # noqa: F401  (registra as tabelas)
from salesos.features.oportunidades import models as _oportunidades_models  # noqa: F401
from salesos.features.tarefas import models as _tarefas_models  # noqa: F401
from salesos.lock import caminho_trava, trava

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
database_url = config.get_main_option("sqlalchemy.url") or Settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Com a trava do banco-alvo (E2, ADR 0005): recusa migrar enquanto um servidor, restore ou
    # recover usa o mesmo arquivo. O `restore --migrar` migra uma cópia, com trava própria.
    try:
        arquivo: Path | None = sqlite_file(database_url)
    except ValueError:
        arquivo = None
    with trava(caminho_trava(arquivo)) if arquivo else nullcontext():
        _migrar_online()


def _migrar_online() -> None:
    engine = create_db_engine(database_url)
    try:
        with engine.connect() as connection:
            # render_as_batch: SQLite não altera colunas em lugar; o Alembic recria a tabela.
            # transactional_ddl: o SQLite suporta DDL em transação, mas o Alembic assume o
            # contrário; sem isso, uma falha (inclusive na checagem de FK) deixaria a migração
            # meio aplicada.
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                transactional_ddl=True,
            )
            # FK desligada só nesta conexão: migrações em batch recriam tabelas e, com FK ligada,
            # apagariam linhas filhas em cascata. A integridade é conferida antes do commit.
            with foreign_keys_disabled(connection), context.begin_transaction():
                context.run_migrations()
                check_foreign_keys(connection)
    finally:
        # Mesmo com erro: no Windows, uma conexão aberta impede apagar a cópia do --migrar.
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
