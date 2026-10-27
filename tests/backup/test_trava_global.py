"""E2: a trava vale para todo servidor (inclusive `uvicorn` direto) e para o Alembic.

Bancos temporários com dados fictícios; o servidor "real" do teste de uvicorn sobe num
subprocesso apontado para a pasta temporária, nunca para `data/`.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from salesos.backup import criar_backup, sha256_arquivo
from salesos.config import Settings
from salesos.lock import Travado, caminho_trava, trava
from salesos.main import create_app
from salesos.restore import restaurar
from tests.backup.conftest import criar_banco
from tests.backup.test_lock import segurar_em_outro_processo
from tests.conftest import TEST_SECRET, migrar


def _app(db: Path) -> TestClient:
    settings = Settings(database_url=f"sqlite:///{db}", secret_key=SecretStr(TEST_SECRET))
    return TestClient(create_app(settings), base_url="http://127.0.0.1")


def _revisao(db: Path) -> str:
    conn = sqlite3.connect(db)
    try:
        return str(conn.execute("SELECT version_num FROM alembic_version").fetchone()[0])
    finally:
        conn.close()


def test_running_app_holds_the_lock_and_releases_it(tmp_path: Path) -> None:
    db = criar_banco(tmp_path / "salesos.db")
    with _app(db), pytest.raises(Travado), trava(caminho_trava(db)):
        pass
    with trava(caminho_trava(db)):  # liberada quando a aplicação encerra
        pass


def test_second_app_on_the_same_database_is_refused(tmp_path: Path) -> None:
    db = criar_banco(tmp_path / "salesos.db")
    with _app(db), pytest.raises(Travado), _app(db):
        pass


def test_app_refuses_to_start_with_pending_restore(tmp_path: Path) -> None:
    db = criar_banco(tmp_path / "salesos.db")
    db.with_name(db.name + ".restore.json").write_text('{"estado": "quiesced"}')
    with pytest.raises(RuntimeError, match="recover"), _app(db):
        pass


def test_uvicorn_started_directly_exits_when_another_server_holds_the_database(
    tmp_path: Path,
) -> None:
    db = criar_banco(tmp_path / "salesos.db")
    ambiente = os.environ | {
        "SALESOS_DATABASE_URL": f"sqlite:///{db}",
        "SALESOS_SECRET_KEY": TEST_SECRET,
        "SALESOS_BACKUP_DIR": str(tmp_path / "backups"),
    }
    roteiro = (
        "import uvicorn; from salesos.main import create_app; "
        "uvicorn.run(create_app, factory=True, host='127.0.0.1', port=0)"
    )
    with _app(db):
        resultado = subprocess.run(  # noqa: S603 (roteiro fixo, interpretador do próprio teste)
            [sys.executable, "-c", roteiro],
            cwd=tmp_path,
            env=ambiente,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert resultado.returncode != 0
    assert "Outro processo do SalesOS" in resultado.stderr


@pytest.mark.parametrize("dono", ["outro-processo", "aplicacao-aberta"])
def test_migration_is_refused_while_the_database_is_in_use(tmp_path: Path, dono: str) -> None:
    db = tmp_path / "salesos.db"
    migrar(db, "0003")
    antes = sha256_arquivo(db)
    if dono == "outro-processo":
        proc = segurar_em_outro_processo(caminho_trava(db))
        try:
            with pytest.raises(Travado):
                migrar(db)
        finally:
            proc.kill()
            proc.wait()
    else:
        with _app(db), pytest.raises(Travado):
            migrar(db)
    assert sha256_arquivo(db) == antes and _revisao(db) == "0003"
    migrar(db)  # livre de novo: a migração segue normalmente
    assert _revisao(db) != "0003"


def test_restore_is_refused_while_the_app_is_running(tmp_path: Path) -> None:
    db = criar_banco(tmp_path / "salesos.db", "Atual")
    backup = criar_backup(db, tmp_path / "backups")
    antes = sha256_arquivo(db)
    with _app(db), pytest.raises(Travado):
        restaurar(db, backup, tmp_path / "backups")
    assert sha256_arquivo(db) == antes
