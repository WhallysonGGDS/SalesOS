"""Recuperação: falha ou queda em cada estado do diário e `recover` idempotente."""

import json
from pathlib import Path

import pytest

from salesos import restore
from salesos.backup import criar_backup
from salesos.restore import controle_pendente, recuperar, restaurar
from tests.backup.conftest import (
    ESTADOS_DESFEITOS,
    Queda,
    assert_original_intacto,
    criar_banco,
    falhar_no_estado,
    nomes,
    sha,
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


def _diario_pendente(
    db: Path, arquivo: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Queda logo depois de aquietar: sobra um diário pendente legítimo."""
    falhar_no_estado(monkeypatch, "quiesced", Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    controle = controle_pendente(db)
    assert controle is not None
    return controle


def _adulterar(controle: Path, **campos: object) -> None:
    dados = json.loads(controle.read_text(encoding="utf-8"))
    dados.update(campos)
    controle.write_text(json.dumps(dados), encoding="utf-8")


@pytest.mark.parametrize(
    "campo", ["staging", "pre_restore"], ids=["staging-fora", "pre-restore-fora"]
)
@pytest.mark.parametrize("forma", ["absoluto", "relativo", "traversal"])
def test_tampered_journal_paths_never_touch_files_outside(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    campo: str,
    forma: str,
) -> None:
    db, arquivo = cenario
    controle = _diario_pendente(db, arquivo, pasta_backups, monkeypatch)
    alvo = tmp_path / "fora" / "vitima.db"
    alvo.parent.mkdir()
    alvo.write_bytes(b"arquivo de outra pessoa")
    caminho = {
        "absoluto": str(alvo),
        "relativo": "../fora/vitima.db",
        "traversal": str(db.parent / ".." / "fora" / "vitima.db"),
    }[forma]
    monkeypatch.chdir(db.parent)
    _adulterar(controle, **{campo: caminho})
    antes = sha(db)

    with pytest.raises(RuntimeError, match="Diário de restauração inválido"):
        recuperar(db)

    assert alvo.read_bytes() == b"arquivo de outra pessoa"
    assert sha(db) == antes
    assert controle_pendente(db) == controle  # continua pendente para análise
    assert not list(db.parent.glob("salesos.db.failed-*"))


@pytest.mark.parametrize(
    "campos",
    [
        pytest.param({"carimbo": "../../fora"}, id="carimbo-traversal"),
        pytest.param({"carimbo": 123}, id="carimbo-nao-texto"),
        pytest.param({"estado": "inventado"}, id="estado-desconhecido"),
        pytest.param({"banco": "/outro/salesos.db"}, id="outro-banco"),
        pytest.param({"staging": None}, id="caminho-nulo"),
        pytest.param({"seguranca": ["lista"]}, id="seguranca-invalida"),
    ],
)
def test_invalid_journal_fields_are_refused_without_moving_anything(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    campos: dict[str, object],
) -> None:
    db, arquivo = cenario
    controle = _diario_pendente(db, arquivo, pasta_backups, monkeypatch)
    _adulterar(controle, **campos)
    arquivos = sorted(p.name for p in db.parent.iterdir())

    with pytest.raises(RuntimeError, match="Diário de restauração inválido"):
        recuperar(db)

    assert sorted(p.name for p in db.parent.iterdir()) == arquivos


@pytest.mark.parametrize(
    "conteudo",
    ["{", "[]", '{"estado": "quiesced"}', "[" * 100_000],
    ids=["json-quebrado", "lista", "sem-campos", "aninhamento-extremo"],
)
def test_unreadable_journal_is_refused_with_clear_message(
    cenario: tuple[Path, Path],
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    conteudo: str,
) -> None:
    db, arquivo = cenario
    controle = _diario_pendente(db, arquivo, pasta_backups, monkeypatch)
    controle.write_text(conteudo, encoding="utf-8")
    with pytest.raises(RuntimeError, match="Diário de restauração inválido"):
        recuperar(db)
    assert controle_pendente(db) == controle


def test_recover_works_with_relative_database_path(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A URL padrão (`sqlite:///data/salesos.db`) é relativa: o caso legítimo continua valendo."""
    origem = criar_banco(tmp_path / "origem" / "salesos.db", "Do backup")
    arquivo = criar_backup(origem, pasta_backups)
    criar_banco(tmp_path / "data" / "salesos.db", "Atual")
    monkeypatch.chdir(tmp_path)
    db = Path("data/salesos.db")
    falhar_no_estado(monkeypatch, "original_moved", Queda())
    with pytest.raises(Queda):
        restaurar(db, arquivo, pasta_backups)
    monkeypatch.undo()
    monkeypatch.chdir(tmp_path)
    assert recuperar(db).estado == "original_moved"
    assert_original_intacto(db)


@pytest.mark.parametrize(
    "marca", ["..", "\u0660" * 8 + "T" + "\u0660" * 12 + "Z"], ids=["pontos", "digitos-unicode"]
)
def test_journal_with_consistent_but_malformed_timestamp_is_refused(
    cenario: tuple[Path, Path], pasta_backups: Path, monkeypatch: pytest.MonkeyPatch, marca: str
) -> None:
    db, arquivo = cenario
    controle = _diario_pendente(db, arquivo, pasta_backups, monkeypatch)
    _adulterar(
        controle,
        carimbo=marca,
        staging=str(db.with_name(f"{db.name}.staging-{marca}")),
        pre_restore=str(db.with_name(f"{db.name}.pre-restore-{marca}")),
    )
    with pytest.raises(RuntimeError, match="Diário de restauração inválido"):
        recuperar(db)
