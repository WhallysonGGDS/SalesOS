"""Restauração com o banco em uso: conexões, outros processos e arquivo ocupado."""

import errno
import os
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from salesos import restore
from salesos.lock import Travado, caminho_trava
from salesos.restore import RestauracaoRecusada, controle_pendente, recuperar, restaurar
from tests.backup.conftest import assert_original_intacto, nomes
from tests.backup.test_lock import segurar_em_outro_processo


def _ociosa(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("SELECT 1 FROM clientes").fetchall()
    return conn


def _leitor(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db, isolation_level=None)
    conn.execute("BEGIN")
    conn.execute("SELECT * FROM clientes").fetchall()
    return conn


def _exclusiva(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db, isolation_level=None)
    conn.execute("PRAGMA locking_mode=EXCLUSIVE")
    conn.execute("BEGIN EXCLUSIVE")
    return conn


def _escritor(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db, isolation_level=None)
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', 'Pendente', 'site')")
    return conn


@pytest.mark.parametrize(
    "abrir",
    [_ociosa, _leitor, _escritor, _exclusiva],
    ids=["ociosa", "leitor", "escritor", "exclusiva"],
)
def test_open_sqlite_connection_aborts_restore(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    abrir: Callable[[Path], sqlite3.Connection],
) -> None:
    db, arquivo = cenario
    conn = abrir(db)
    try:
        with pytest.raises(RestauracaoRecusada, match="Feche os programas"):
            restaurar(db, arquivo, pasta_backups)
    finally:
        conn.rollback()
        conn.close()
    assert_original_intacto(db)
    assert not list(db.parent.glob("*.pre-restore-*"))


ABRIR_E_ESPERAR = """
import sqlite3, sys, time
conn = sqlite3.connect(sys.argv[1])
conn.execute("SELECT 1 FROM clientes").fetchall()
print("ok", flush=True)
time.sleep(60)
"""


def test_idle_connection_in_other_process_aborts_restore(
    cenario: tuple[Path, Path], pasta_backups: Path
) -> None:
    db, arquivo = cenario
    proc = subprocess.Popen(  # noqa: S603 (roteiro fixo, interpretador do próprio teste)
        [sys.executable, "-c", ABRIR_E_ESPERAR, str(db)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert proc.stdout is not None and proc.stdout.readline().strip() == "ok"
        with pytest.raises(RestauracaoRecusada, match="Feche os programas"):
            restaurar(db, arquivo, pasta_backups)
    finally:
        proc.kill()
        proc.wait()
    assert_original_intacto(db)


def test_running_salesos_process_blocks_restore(
    cenario: tuple[Path, Path], pasta_backups: Path
) -> None:
    db, arquivo = cenario
    proc = segurar_em_outro_processo(caminho_trava(db))
    try:
        with pytest.raises(Travado):
            restaurar(db, arquivo, pasta_backups)
    finally:
        proc.kill()
        proc.wait()
    assert_original_intacto(db)


def _replace_falhando(monkeypatch: pytest.MonkeyPatch, db: Path, falhas: int) -> dict[str, int]:
    """`os.replace` recusa trocar o caminho do banco (como o Windows com o arquivo aberto)."""
    real = os.replace
    contador = {"falhas": 0}

    def replace(origem: Any, destino: Any) -> None:
        if Path(destino) == db and contador["falhas"] < falhas:
            contador["falhas"] += 1
            raise PermissionError(errno.EACCES, "arquivo em uso")
        real(origem, destino)

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr("salesos.restore.time.sleep", lambda _s: None)
    return contador


def test_swap_is_retried_when_file_is_busy(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    contador = _replace_falhando(monkeypatch, db, falhas=3)
    restaurar(db, arquivo, pasta_backups)
    assert contador["falhas"] == 3
    assert nomes(db) == ["Do backup"]


def test_swap_that_keeps_failing_rolls_back(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    _replace_falhando(monkeypatch, db, falhas=10**6)
    with pytest.raises(PermissionError):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    assert not db.exists()  # nem a volta conseguiu: o original espera intacto ao lado
    (guardado,) = db.parent.glob("salesos.db.pre-restore-*")
    assert nomes(guardado) == ["Atual"]
    assert controle_pendente(db) is not None
    recuperar(db)
    assert_original_intacto(db)


@pytest.mark.skipif(sys.platform != "win32", reason="só o Windows recusa trocar arquivo aberto")
def test_windows_refuses_swap_while_other_process_holds_the_file(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Abre o banco depois da sondagem (sem SQLite) e prova que a troca falha e é desfeita."""
    db, arquivo = cenario
    monkeypatch.setattr("salesos.restore.time.sleep", lambda _s: None)
    segurar = (
        "import sys, time\nf = open(sys.argv[1], 'rb')\nprint('ok', flush=True)\ntime.sleep(60)"
    )
    procs: list[subprocess.Popen[str]] = []
    original = restore._gravar_estado

    def gravar(controle: Path, dados: dict[str, Any], estado: str) -> None:
        original(controle, dados, estado)
        if estado == "safety_backed_up":
            proc = subprocess.Popen(  # noqa: S603 (roteiro fixo)
                [sys.executable, "-c", segurar, str(db)], stdout=subprocess.PIPE, text=True
            )
            assert proc.stdout is not None and proc.stdout.readline().strip() == "ok"
            procs.append(proc)

    monkeypatch.setattr(restore, "_gravar_estado", gravar)
    try:
        with pytest.raises(OSError):
            restaurar(db, arquivo, pasta_backups)
    finally:
        for proc in procs:
            proc.kill()
            proc.wait()
    monkeypatch.undo()
    recuperar(db)
    assert_original_intacto(db)
