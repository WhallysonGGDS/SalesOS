"""B1: falhas, interrupções, sobras, permissões e logs de `restore --migrar` (dados fictícios)."""

import logging
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from alembic import command

from salesos.backup import caminho_manifesto, criar_backup, verificar_backup
from salesos.backup import publicar as backup_publicar
from salesos.migracao_backup import migrar_backup
from salesos.restore import RestauracaoRecusada, recuperar, restaurar
from tests.backup.conftest import (
    ANTIGO,
    alterar_bytes,
    backup_antigo,
    escutar,
    estado,
    migrados,
    nomes,
    temporarios,
)

posix = pytest.mark.skipif(sys.platform == "win32", reason="bits POSIX; no Windows valem ACLs")


@pytest.mark.parametrize("erro", [RuntimeError("falha injetada"), KeyboardInterrupt()])
def test_failure_during_migration_cleans_up_and_changes_nothing(
    tmp_path: Path,
    atual: Path,
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    erro: BaseException,
) -> None:
    arquivo = backup_antigo(tmp_path)
    original = estado(arquivo, caminho_manifesto(arquivo))
    banco = estado(atual)

    def checagem_que_falha(_conexao: Any) -> None:
        raise erro

    # O env.py importa a checagem de FK a cada migração: a falha acontece no meio do upgrade.
    monkeypatch.setattr("salesos.db.check_foreign_keys", checagem_que_falha)
    with pytest.raises((RestauracaoRecusada, KeyboardInterrupt)):
        migrar_backup(arquivo, pasta_backups)

    assert estado(arquivo, caminho_manifesto(arquivo)) == original
    assert estado(atual) == banco
    assert temporarios(pasta_backups) == [] and migrados(pasta_backups) == []


def test_recover_reports_leftovers_of_an_abrupt_stop_without_deleting(
    tmp_path: Path, atual: Path, pasta_backups: Path
) -> None:
    valido = criar_backup(atual, pasta_backups)
    sobra = pasta_backups / ".migracao-20261027T000000000000Z"
    sobra.mkdir()
    (sobra / "salesos.db").write_bytes(b"copia parcial")
    (pasta_backups / "migracao-sem-ponto").mkdir()  # nome parecido: não é nosso
    (pasta_backups / ".migracao-arquivo").write_text("não é pasta")

    relatorio = recuperar(atual, pasta_backups)

    assert sobra in relatorio.residuos
    assert pasta_backups / "migracao-sem-ponto" not in relatorio.residuos
    assert pasta_backups / ".migracao-arquivo" not in relatorio.residuos
    assert valido not in relatorio.residuos
    assert (sobra / "salesos.db").exists() and valido.exists()


@posix
def test_migrated_backup_and_temporary_folder_are_private(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anterior = os.umask(0o022)
    try:
        arquivo = backup_antigo(tmp_path)
        modos: list[int] = []
        upgrade_real = command.upgrade

        def upgrade(config: Any, revisao: str) -> None:
            url = str(config.get_main_option("sqlalchemy.url"))
            copia = Path(url.removeprefix("sqlite:///"))
            modos.extend(stat.S_IMODE(p.stat().st_mode) for p in (copia.parent, copia))
            upgrade_real(config, revisao)

        monkeypatch.setattr(command, "upgrade", upgrade)
        migrado = migrar_backup(arquivo, pasta_backups)
    finally:
        os.umask(anterior)
    assert modos == [0o700, 0o600]
    assert stat.S_IMODE(migrado.stat().st_mode) == 0o600
    assert stat.S_IMODE(caminho_manifesto(migrado).stat().st_mode) == 0o600


def test_migration_logs_and_prints_no_client_data(
    tmp_path: Path,
    atual: Path,
    pasta_backups: Path,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    arquivo = backup_antigo(tmp_path)
    capfd.readouterr()
    escutar(caplog)
    logging.getLogger("salesos.migracao_backup").debug("sonda do teste")
    restaurar(atual, migrar_backup(arquivo, pasta_backups), pasta_backups)
    saida = capfd.readouterr()
    assert "sonda do teste" in caplog.text  # a captura funciona: o teste não é vazio
    for texto in (caplog.text, saida.out, saida.err):
        assert ANTIGO.lower() not in texto.lower()


def test_copy_that_differs_from_the_manifest_is_refused(
    tmp_path: Path, atual: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O arquivo pode mudar entre a verificação e a cópia: a cópia é conferida de novo."""
    arquivo = backup_antigo(tmp_path)
    original = estado(arquivo, caminho_manifesto(arquivo))
    copiar_real = shutil.copyfile

    def copiar_e_alterar(origem: Any, destino: Any) -> Any:
        resultado = copiar_real(origem, destino)
        alterar_bytes(Path(destino))
        return resultado

    monkeypatch.setattr(shutil, "copyfile", copiar_e_alterar)
    with pytest.raises(RestauracaoRecusada, match="SHA-256"):
        migrar_backup(arquivo, pasta_backups)
    assert estado(arquivo, caminho_manifesto(arquivo)) == original
    assert temporarios(pasta_backups) == [] and migrados(pasta_backups) == []


def test_unexpected_alembic_error_becomes_a_refusal(
    tmp_path: Path, atual: Path, pasta_backups: Path
) -> None:
    """Duas linhas em alembic_version: o Alembic falha com CommandError, que não pode escapar."""
    arquivo = backup_antigo(tmp_path, sql="INSERT INTO alembic_version VALUES ('0001');")
    banco = estado(atual)
    with pytest.raises(RestauracaoRecusada, match="Nada foi alterado"):
        migrar_backup(arquivo, pasta_backups)
    assert estado(atual) == banco
    assert temporarios(pasta_backups) == [] and migrados(pasta_backups) == []


def test_backup_folder_with_percent_sign_works(tmp_path: Path, atual: Path) -> None:
    pasta = tmp_path / "backups 100% teste"
    restaurar(atual, migrar_backup(backup_antigo(tmp_path), pasta), pasta)
    assert nomes(atual) == [ANTIGO]


def test_interruption_before_verification_leaves_no_unverified_migrated_backup(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = backup_antigo(tmp_path)

    def verificacao_interrompida(*_a: Any, **_k: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "salesos.migracao_backup.verificar_backup",
        _primeira_real_depois(verificacao_interrompida),
    )
    with pytest.raises(KeyboardInterrupt):
        migrar_backup(arquivo, pasta_backups)
    assert migrados(pasta_backups) == [] and temporarios(pasta_backups) == []


def _primeira_real_depois(falha: Any) -> Any:
    """A primeira chamada (o backup antigo) é real; as seguintes falham."""
    real = verificar_backup
    chamadas = {"n": 0}

    def verificar(*args: Any, **kwargs: Any) -> Any:
        chamadas["n"] += 1
        return real(*args, **kwargs) if chamadas["n"] == 1 else falha(*args, **kwargs)

    return verificar


def test_cleanup_that_fails_is_warned_and_reported_by_recover(
    tmp_path: Path,
    atual: Path,
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No Windows, um arquivo aberto impede apagar a cópia: o aviso e o recover a mostram."""
    arquivo = backup_antigo(tmp_path)
    escutar(caplog)
    monkeypatch.setattr(shutil, "rmtree", lambda *_a, **_k: None)
    migrar_backup(arquivo, pasta_backups)
    (sobra,) = pasta_backups.glob(".migracao-*")
    assert "não foi apagada" in caplog.text
    assert ANTIGO.lower() not in caplog.text.lower()
    assert sobra in recuperar(atual, pasta_backups).residuos


@pytest.mark.parametrize("erro", [OSError("disco cheio"), KeyboardInterrupt()])
def test_failure_between_the_two_publications_leaves_no_migrated_backup(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch, erro: BaseException
) -> None:
    """O .db publicado sem o manifesto seria um backup inútil fora da pasta temporária."""
    arquivo = backup_antigo(tmp_path)
    publicar_real = backup_publicar
    chamadas = {"n": 0}

    def publicar(origem: Path, destino: Path) -> None:
        chamadas["n"] += 1
        if chamadas["n"] == 2:  # o manifesto
            raise erro
        publicar_real(origem, destino)

    monkeypatch.setattr("salesos.migracao_backup.publicar", publicar)
    with pytest.raises((RestauracaoRecusada, KeyboardInterrupt)):
        migrar_backup(arquivo, pasta_backups)
    assert chamadas["n"] == 2
    assert migrados(pasta_backups) == [] and temporarios(pasta_backups) == []
