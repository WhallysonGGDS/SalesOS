"""Ponto de entrada `salesos`: servidor, backup, restore e recover (banco temporário)."""

import sys
from pathlib import Path
from typing import Any

import pytest

from salesos import main
from salesos.lock import Travado, caminho_trava, trava
from salesos.restore import controle_pendente
from tests.backup.conftest import criar_banco, nomes


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


def test_server_holds_the_lock_while_running(db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vistos: list[str] = []

    def uvicorn_falso(*_a: Any, **_k: Any) -> None:
        try:
            with trava(caminho_trava(db)):
                vistos.append("livre")
        except Travado:
            vistos.append("travada")

    monkeypatch.setattr("salesos.main.uvicorn.run", uvicorn_falso)
    _rodar(monkeypatch)
    assert vistos == ["travada"]
    with trava(caminho_trava(db)):  # liberada ao encerrar
        pass


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
