"""Recuperação: falha ou queda em cada estado do diário e `recover` idempotente."""

from pathlib import Path

import pytest

from salesos import restore
from salesos.restore import controle_pendente, recuperar, restaurar
from tests.backup.conftest import (
    ESTADOS_DESFEITOS,
    Queda,
    assert_original_intacto,
    falhar_no_estado,
    nomes,
)


@pytest.mark.parametrize("estado", ESTADOS_DESFEITOS)
def test_failure_in_each_state_rolls_back_automatically(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    estado: str,
) -> None:
    db, arquivo = cenario
    falhar_no_estado(monkeypatch, estado, RuntimeError("falha injetada"))
    with pytest.raises(RuntimeError, match="falha injetada"):
        restaurar(db, arquivo, pasta_backups)
    assert_original_intacto(db)
    assert list(db.parent.glob("salesos.db.restore-*-aborted.json"))


def test_failure_after_verified_keeps_restored_database(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    falhar_no_estado(monkeypatch, "verified", RuntimeError("falha injetada"))
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
    falhar_no_estado(monkeypatch, estado, Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    assert controle_pendente(db) is not None
    monkeypatch.undo()

    assert recuperar(db).estado == estado
    assert_original_intacto(db)
    preservados = {n for n in _arquivos(db, pasta_backups) if ".staging" not in n}
    assert recuperar(db).estado is None
    assert_original_intacto(db)
    assert preservados <= _arquivos(db, pasta_backups)  # nada é apagado na recuperação


def test_crash_after_verified_keeps_restored_database(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db, arquivo = cenario
    falhar_no_estado(monkeypatch, "verified", Queda())
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
    assert_original_intacto(db)
    if chamada == 2:  # o banco novo é guardado, nunca apagado
        assert len(list(db.parent.glob("salesos.db.failed-*"))) == 1


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
