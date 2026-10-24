"""Permissões restritivas para arquivos com dados pessoais (POSIX; no Windows valem as ACLs)."""

import os
import stat
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from salesos import db as db_module
from salesos.backup import caminho_manifesto, criar_backup
from salesos.db import create_db_engine
from salesos.restore import restaurar
from tests.backup.conftest import criar_banco

posix = pytest.mark.skipif(sys.platform == "win32", reason="bits POSIX; no Windows valem ACLs")


def _modo(caminho: Path) -> int:
    return stat.S_IMODE(caminho.stat().st_mode)


@pytest.fixture(autouse=True)
def _umask_permissiva() -> Iterator[None]:
    """Com umask 022 (o comum), sem correção os arquivos sairiam 0644 e as pastas 0755."""
    anterior = os.umask(0o022)
    yield
    os.umask(anterior)


@posix
def test_database_file_and_wal_are_private(tmp_path: Path) -> None:
    db = tmp_path / "dados" / "salesos.db"
    engine = create_db_engine(f"sqlite:///{db}")
    with engine.connect() as conn:
        conn.exec_driver_sql("CREATE TABLE t (x)")
        conn.commit()
        assert _modo(db) == 0o600
        assert _modo(Path(f"{db}-wal")) == 0o600
    engine.dispose()


@posix
def test_data_folder_created_by_salesos_is_private_but_existing_is_untouched(
    tmp_path: Path,
) -> None:
    nova = tmp_path / "nova" / "salesos.db"
    create_db_engine(f"sqlite:///{nova}").dispose()
    assert _modo(nova.parent) == 0o700
    existente = tmp_path / "existente"
    existente.mkdir(mode=0o755)
    create_db_engine(f"sqlite:///{existente / 'salesos.db'}").dispose()
    assert _modo(existente) == 0o755


@posix
def test_backup_files_and_folder_are_private(tmp_path: Path, pasta_backups: Path) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    assert _modo(pasta_backups) == 0o700
    assert _modo(arquivo) == 0o600
    assert _modo(caminho_manifesto(arquivo)) == 0o600


@posix
def test_restore_leaves_every_copy_private(tmp_path: Path, pasta_backups: Path) -> None:
    origem = criar_banco(tmp_path / "origem" / "salesos.db", "Do backup")
    arquivo = criar_backup(origem, pasta_backups)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    os.chmod(db, 0o644)  # banco antigo, criado antes desta correção
    pre = restaurar(db, arquivo, pasta_backups)
    copias = [db, pre, *pasta_backups.glob("pre-restore-*"), *db.parent.glob("*.restore-*.json")]
    assert {c.name: _modo(c) for c in copias} == {c.name: 0o600 for c in copias}


def test_windows_does_not_pretend_posix_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No Windows, os.chmod só mexe no "somente leitura": não é chamado."""
    chamadas: list[object] = []
    monkeypatch.setattr("salesos.db.sys.platform", "win32")
    monkeypatch.setattr("salesos.db.os.chmod", lambda *a: chamadas.append(a))
    arquivo = tmp_path / "x"
    arquivo.write_text("x")
    db_module.restringir(arquivo)
    assert chamadas == []
