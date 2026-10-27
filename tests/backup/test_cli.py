"""Ponto de entrada `salesos`: servidor, backup, restore e recover (banco temporário)."""

import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

from salesos import main
from salesos.backup import criar_backup
from salesos.lock import Travado, caminho_trava, trava
from salesos.restore import controle_pendente
from tests.backup.conftest import criar_banco, nomes
from tests.backup.test_lock import segurar_em_outro_processo
from tests.conftest import migrar


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    caminho = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    monkeypatch.setenv("SALESOS_DATABASE_URL", f"sqlite:///{caminho}")
    monkeypatch.setenv("SALESOS_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr("salesos.main.uvicorn.run", _servidor_proibido)
    return caminho


def _servidor_proibido(*_a: Any, **_k: Any) -> None:
    raise AssertionError("o servidor real não pode subir nos testes")


def _rodar(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["salesos", *args])
    main.run()


def test_server_command_leaves_the_lock_to_the_app(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Quem segura a trava é a inicialização da aplicação (E2): se o comando a segurasse
    # durante o uvicorn.run, a aplicação no mesmo processo se recusaria a subir.
    vistos: list[str] = []

    def uvicorn_falso(*_a: Any, **k: Any) -> None:
        vistos.append(f"access_log={k.get('access_log')}")  # o log de acesso traria ?q=<nome>
        try:
            with trava(caminho_trava(db)):
                vistos.append("livre")
        except Travado:
            vistos.append("travada")

    monkeypatch.setattr("salesos.main.uvicorn.run", uvicorn_falso)
    _rodar(monkeypatch)
    assert vistos == ["access_log=False", "livre"]


def test_server_command_refuses_when_another_process_holds_the_database(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamado: list[bool] = []
    monkeypatch.setattr("salesos.main.uvicorn.run", lambda *a, **k: chamado.append(True))
    proc = segurar_em_outro_processo(caminho_trava(db))
    try:
        with pytest.raises(SystemExit, match="Outro processo do SalesOS"):
            _rodar(monkeypatch)
    finally:
        proc.kill()
        proc.wait()
    assert chamado == []


def test_server_refuses_to_start_with_pending_restore(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db.with_name(db.name + ".restore.json").write_text('{"estado": "quiesced"}')
    chamado: list[bool] = []
    monkeypatch.setattr("salesos.main.uvicorn.run", lambda *a, **k: chamado.append(True))
    with pytest.raises(SystemExit, match="recover"):
        _rodar(monkeypatch)
    assert chamado == []


def test_backup_restore_and_recover_commands(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _rodar(monkeypatch, "backup")
    (arquivo,) = (tmp_path / "backups").glob("salesos-*.db")
    assert str(arquivo) in capsys.readouterr().out

    _rodar(monkeypatch, "restore", str(arquivo))
    assert nomes(db) == ["Atual"]
    assert controle_pendente(db) is None

    _rodar(monkeypatch, "recover")
    assert "Nenhuma restauração pendente" in capsys.readouterr().out


def test_restore_of_missing_file_exits_with_message_and_keeps_database(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(SystemExit, match=r"inexistente\.db"):
        _rodar(monkeypatch, "restore", str(tmp_path / "inexistente.db"))
    assert nomes(db) == ["Atual"]
    assert controle_pendente(db) is None


def test_backup_of_missing_database_exits_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SALESOS_DATABASE_URL", f"sqlite:///{tmp_path / 'nao-existe.db'}")
    monkeypatch.setenv("SALESOS_BACKUP_DIR", str(tmp_path / "backups"))
    with pytest.raises(SystemExit, match="Banco não encontrado"):
        _rodar(monkeypatch, "backup")
    assert not (tmp_path / "backups").exists()
    assert not (tmp_path / "nao-existe.db").exists()


def test_backup_command_reports_locked_database_instead_of_hanging(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("salesos.backup.ESPERA_BLOQUEIO", 0.2)
    dono = sqlite3.connect(db, isolation_level=None)
    dono.execute("PRAGMA locking_mode=EXCLUSIVE")
    dono.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(SystemExit, match="bloqueado por outro programa"):
            _rodar(monkeypatch, "backup")
    finally:
        dono.rollback()
        dono.close()


def test_restore_with_migrate_flag_restores_an_old_backup(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    antigo = tmp_path / "antigo" / "salesos.db"
    migrar(antigo, "0002")
    conn = sqlite3.connect(antigo)
    conn.execute("INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', 'Do backup', 'site')")
    conn.commit()
    conn.close()
    arquivo = criar_backup(antigo, tmp_path / "antigos")

    with pytest.raises(SystemExit, match="revisão do esquema 0002"):
        _rodar(monkeypatch, "restore", str(arquivo))  # sem --migrar: recusa de sempre
    assert nomes(db) == ["Atual"]

    _rodar(monkeypatch, "restore", str(arquivo), "--migrar")
    saida = capsys.readouterr().out
    assert "Backup migrado" in saida and "migrado-" in saida
    assert nomes(db) == ["Do backup"]
