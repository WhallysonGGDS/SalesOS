"""Restauração: troca, recusa de backups inválidos e falhas antes da troca."""

import errno
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from salesos import restore
from salesos.backup import criar_backup, verificar_backup
from salesos.restore import RestauracaoRecusada, controle_pendente, restaurar
from tests.backup.conftest import (
    Queda,
    assert_original_intacto,
    criar_banco,
    falhar_no_estado,
    modo,
    nomes,
    sha,
    sobras,
)


def test_restore_swaps_database_and_keeps_every_copy(
    cenario: tuple[Path, Path], pasta_backups: Path
) -> None:
    db, arquivo = cenario
    pre_restore = restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Do backup"]
    assert modo(db) == "wal"
    assert nomes(pre_restore) == ["Atual"]
    assert controle_pendente(db) is None
    assert sobras(db) == []
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
    antes = sha(db)
    estragar(arquivo)
    with pytest.raises(RestauracaoRecusada):
        restaurar(db, arquivo, pasta_backups)
    assert_original_intacto(db)
    assert sha(db) == antes
    assert not list(db.parent.glob("*.pre-restore-*"))


def test_backup_with_extra_trigger_is_refused_before_any_change(
    tmp_path: Path, pasta_backups: Path
) -> None:
    origem = criar_banco(tmp_path / "origem" / "salesos.db", "Do backup")
    conn = sqlite3.connect(origem)
    conn.executescript(
        "CREATE TABLE copia (nome TEXT); CREATE TRIGGER espiao BEFORE UPDATE ON clientes "
        "BEGIN INSERT INTO copia VALUES (old.nome); END;"
    )
    conn.close()
    arquivo = criar_backup(origem, pasta_backups)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    with pytest.raises(RestauracaoRecusada, match="estrutura"):
        restaurar(db, arquivo, pasta_backups)
    assert_original_intacto(db)
    assert not list(db.parent.glob("*.pre-restore-*"))


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
    assert_original_intacto(db)


def test_pending_control_blocks_new_restore(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    falhar_no_estado(monkeypatch, "quiesced", Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    with pytest.raises(RestauracaoRecusada, match="recover"):
        restaurar(db, arquivo, pasta_backups)
