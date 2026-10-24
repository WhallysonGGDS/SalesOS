"""Restauração com diário de estados e recuperação (dados fictícios, só em pasta temporária)."""

import errno
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from salesos import restore
from salesos.backup import criar_backup, verificar_backup
from salesos.lock import Travado, caminho_trava
from salesos.restore import RestauracaoRecusada, controle_pendente, recuperar, restaurar
from tests.backup.conftest import criar_banco, modo, nomes
from tests.backup.test_lock import segurar_em_outro_processo

ESTADOS_DESFEITOS = ["validating", "quiesced", "safety_backed_up", "original_moved", "swapped"]


class Queda(BaseException):
    """Simula o processo morrendo: nenhum `except Exception` roda."""


def _sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@pytest.fixture
def cenario(tmp_path: Path, pasta_backups: Path) -> tuple[Path, Path]:
    """Banco "atual" e um backup verificado de outro banco ("Do backup")."""
    origem = criar_banco(tmp_path / "origem" / "salesos.db", "Do backup")
    arquivo = criar_backup(origem, pasta_backups)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    return db, arquivo


def _sobras(db: Path) -> list[str]:
    return sorted(p.name for p in db.parent.iterdir() if ".staging" in p.name)


def _assert_original_intacto(db: Path) -> None:
    assert nomes(db) == ["Atual"]
    assert modo(db) == "wal"
    assert controle_pendente(db) is None
    assert _sobras(db) == []


def test_restore_swaps_database_and_keeps_every_copy(
    cenario: tuple[Path, Path], pasta_backups: Path
) -> None:
    db, arquivo = cenario
    pre_restore = restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Do backup"]
    assert modo(db) == "wal"
    assert nomes(pre_restore) == ["Atual"]
    assert controle_pendente(db) is None
    assert _sobras(db) == []
    seguranca = [p for p in pasta_backups.glob("pre-restore-*.db")]
    assert len(seguranca) == 1 and nomes(seguranca[0]) == ["Atual"]
    verificar_backup(seguranca[0])
    arquivados = list(db.parent.glob("salesos.db.restore-*-done.json"))
    assert len(arquivados) == 1


@pytest.mark.parametrize(
    "estragar",
    [
        pytest.param(lambda a: a.write_bytes(b"lixo"), id="corrompido"),
        pytest.param(lambda a: a.with_name(a.name + ".json").unlink(), id="sem-manifesto"),
        pytest.param(
            lambda a: a.with_name(a.name + ".json").write_text(
                json.dumps({"sha256": "0" * 64, "revisao": "0002"})
            ),
            id="hash-divergente",
        ),
    ],
)
def test_invalid_backup_is_refused_before_any_change(
    cenario: tuple[Path, Path], pasta_backups: Path, estragar: Callable[[Path], Any]
) -> None:
    db, arquivo = cenario
    antes = _sha(db)
    estragar(arquivo)
    with pytest.raises(RestauracaoRecusada):
        restaurar(db, arquivo, pasta_backups)
    _assert_original_intacto(db)
    assert _sha(db) == antes
    assert not list(db.parent.glob("*.pre-restore-*"))


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
    _assert_original_intacto(db)
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
    _assert_original_intacto(db)


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
    _assert_original_intacto(db)


def test_backup_older_than_anonymization_needs_explicit_consent(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Pessoa Ficticia")
    arquivo = criar_backup(db, pasta_backups)
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE clientes SET nome = 'Cliente anonimizado #1', anonimizado_em = CURRENT_TIMESTAMP"
    )
    conn.commit()
    conn.close()
    with pytest.raises(RestauracaoRecusada, match="anonimiza"):
        restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Cliente anonimizado #1"]
    restaurar(db, arquivo, pasta_backups, aceitar_reintroducao=True)
    assert nomes(db) == ["Pessoa Ficticia"]


def test_disk_full_while_staging_keeps_original(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario

    def disco_cheio(_origem: Path, destino: Path) -> None:
        destino.write_bytes(b"parcial")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(restore, "_copiar", disco_cheio)
    with pytest.raises(OSError, match="space"):
        restaurar(db, arquivo, pasta_backups)
    _assert_original_intacto(db)


def _falhar_no_estado(monkeypatch: pytest.MonkeyPatch, alvo: str, erro: BaseException) -> None:
    original = restore._gravar_estado

    def gravar(controle: Path, dados: dict[str, Any], estado: str) -> None:
        original(controle, dados, estado)
        if estado == alvo:
            raise erro

    monkeypatch.setattr(restore, "_gravar_estado", gravar)


@pytest.mark.parametrize("estado", ESTADOS_DESFEITOS)
def test_failure_in_each_state_rolls_back_automatically(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    estado: str,
) -> None:
    db, arquivo = cenario
    _falhar_no_estado(monkeypatch, estado, RuntimeError("falha injetada"))
    with pytest.raises(RuntimeError, match="falha injetada"):
        restaurar(db, arquivo, pasta_backups)
    _assert_original_intacto(db)
    assert list(db.parent.glob("salesos.db.restore-*-aborted.json"))


def test_failure_after_verified_keeps_restored_database(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    _falhar_no_estado(monkeypatch, "verified", RuntimeError("falha injetada"))
    with pytest.raises(RuntimeError):
        restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Do backup"]
    assert controle_pendente(db) is None


def _arquivos(db: Path, pasta_backups: Path) -> set[str]:
    return {p.name for p in [*db.parent.iterdir(), *pasta_backups.iterdir()]}


@pytest.mark.parametrize("estado", ESTADOS_DESFEITOS)
def test_crash_in_each_state_is_recovered_idempotently(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    estado: str,
) -> None:
    db, arquivo = cenario
    _falhar_no_estado(monkeypatch, estado, Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    assert controle_pendente(db) is not None
    monkeypatch.undo()

    assert recuperar(db).estado == estado
    _assert_original_intacto(db)
    preservados = {n for n in _arquivos(db, pasta_backups) if ".staging" not in n}
    assert recuperar(db).estado is None
    _assert_original_intacto(db)
    assert preservados <= _arquivos(db, pasta_backups)  # nada é apagado na recuperação


def test_crash_after_verified_keeps_restored_database(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    _falhar_no_estado(monkeypatch, "verified", Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    assert recuperar(db).estado == "verified"
    assert nomes(db) == ["Do backup"]
    assert controle_pendente(db) is None


@pytest.mark.parametrize("chamada", [1, 2], ids=["ao-mover-original", "ao-trocar"])
def test_crash_between_file_move_and_state_write_is_recovered(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    chamada: int,
) -> None:
    db, arquivo = cenario
    original = restore._mover
    contador = {"n": 0}

    def mover(origem: Path, destino: Path) -> None:
        original(origem, destino)
        contador["n"] += 1
        if contador["n"] == chamada:
            raise Queda()

    monkeypatch.setattr(restore, "_mover", mover)
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    recuperar(db)
    _assert_original_intacto(db)
    if chamada == 2:  # o banco novo é guardado, nunca apagado
        assert len(list(db.parent.glob("salesos.db.failed-*"))) == 1


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
    _assert_original_intacto(db)


def test_pending_control_blocks_new_restore(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    _falhar_no_estado(monkeypatch, "quiesced", Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    with pytest.raises(RestauracaoRecusada, match="recover"):
        restaurar(db, arquivo, pasta_backups)


def test_recover_reports_leftover_backup_temporaries(
    cenario: tuple[Path, Path], pasta_backups: Path
) -> None:
    db, _arquivo = cenario
    sobra = pasta_backups / "salesos-20261024T000000000000Z.db.tmp"
    sobra.write_bytes(b"parcial")
    relatorio = recuperar(db, pasta_backups)
    assert relatorio.estado is None
    assert relatorio.residuos == [sobra]
    assert sobra.exists()  # só relata: apagar é decisão do usuário


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
    _assert_original_intacto(db)
