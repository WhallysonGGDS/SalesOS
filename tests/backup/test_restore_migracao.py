"""B1: `restore --migrar` migra uma cópia temporária de um backup antigo (dados fictícios)."""

import json
import logging
import os
import shutil
import sqlite3
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from alembic import command

from salesos.backup import caminho_manifesto, criar_backup, revisao_atual, verificar_backup
from salesos.backup import publicar as backup_publicar
from salesos.migracao_backup import migrar_backup, revisoes_anteriores
from salesos.restore import RestauracaoRecusada, recuperar, restaurar
from tests.backup.conftest import criar_banco, nomes, sha
from tests.conftest import migrar

ANTIGO = "Qwxclienteantigo"
posix = pytest.mark.skipif(sys.platform == "win32", reason="bits POSIX; no Windows valem ACLs")


def _backup_antigo(base: Path, revisao: str = "0002", sql: str | None = None) -> Path:
    """Banco fictício parado na `revisao`, com um cliente, e o backup verificado dele."""
    db = base / f"antigo-{revisao}" / "salesos.db"
    migrar(db, revisao)
    conn = sqlite3.connect(db)
    if revisao != "0001":  # a linha de base não tem tabelas de negócio
        conn.execute(
            "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', ?, 'site')", (ANTIGO,)
        )
    if sql:
        conn.executescript(sql)
    conn.commit()
    conn.close()
    return criar_backup(db, base / f"antigo-{revisao}" / "backups")


def _escutar(caplog: pytest.LogCaptureFixture) -> None:
    """O `migrar()` dos testes usa o alembic.ini, cujo fileConfig tira o handler do caplog."""
    raiz = logging.getLogger()
    if caplog.handler not in raiz.handlers:
        raiz.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def _estado(*arquivos: Path) -> list[tuple[str, int]]:
    return [(sha(a), a.stat().st_mtime_ns) for a in arquivos]


def _temporarios(pasta: Path) -> list[str]:
    return sorted(p.name for p in pasta.glob(".migracao-*")) if pasta.exists() else []


def _migrados(pasta: Path) -> list[str]:
    return sorted(p.name for p in pasta.glob("migrado-*")) if pasta.exists() else []


@pytest.fixture
def atual(tmp_path: Path) -> Path:
    return criar_banco(tmp_path / "dados" / "salesos.db", "Atual")


def test_valid_old_backup_is_migrated_and_restored(
    tmp_path: Path, atual: Path, pasta_backups: Path
) -> None:
    arquivo = _backup_antigo(tmp_path)
    original = _estado(arquivo, caminho_manifesto(arquivo))
    with pytest.raises(RestauracaoRecusada, match="revisão do esquema 0002"):
        restaurar(atual, arquivo, pasta_backups)  # sem --migrar: comportamento de sempre

    migrado = migrar_backup(arquivo, pasta_backups)
    assert migrado.parent == pasta_backups and migrado.name.startswith("migrado-")
    assert verificar_backup(migrado)["revisao"] == revisao_atual()
    restaurar(atual, migrado, pasta_backups)

    assert nomes(atual) == [ANTIGO]
    conn = sqlite3.connect(atual)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == revisao_atual()
    assert conn.execute("SELECT count(*) FROM oportunidades").fetchone()[0] == 0
    conn.close()
    assert _estado(arquivo, caminho_manifesto(arquivo)) == original
    assert _temporarios(pasta_backups) == []


def test_backup_already_at_current_revision_needs_no_migration(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "outro" / "salesos.db", "Ja atual")
    arquivo = criar_backup(db, tmp_path / "outro" / "backups")
    assert migrar_backup(arquivo, pasta_backups) == arquivo
    assert _migrados(pasta_backups) == [] and _temporarios(pasta_backups) == []


def _alterar_bytes(arquivo: Path) -> None:
    with arquivo.open("r+b") as f:
        f.seek(5000)
        f.write(b"X")


def _trocar_por_lixo(arquivo: Path) -> None:
    """Arquivo que não é SQLite, com manifesto coerente (o SHA confere)."""
    arquivo.write_bytes(os.urandom(8192))
    manifesto = caminho_manifesto(arquivo)
    conteudo = json.loads(manifesto.read_text(encoding="utf-8")) | {"sha256": sha(arquivo)}
    manifesto.write_text(json.dumps(conteudo), encoding="utf-8")


TRIGGER = (
    "CREATE TABLE copia (nome TEXT); CREATE TRIGGER espiao BEFORE UPDATE ON clientes "
    "BEGIN INSERT INTO copia VALUES (old.nome); END;"
)
ORFAO = "PRAGMA foreign_keys=OFF; INSERT INTO contatos (cliente_id, nome) VALUES (999, 'Orfao');"
DESCONHECIDA = "UPDATE alembic_version SET version_num = '9999';"


@pytest.mark.parametrize(
    ("sql", "estragar", "mensagem"),
    [
        pytest.param(None, _alterar_bytes, "SHA-256", id="alterado-depois-do-manifesto"),
        pytest.param(None, _trocar_por_lixo, "integridade", id="nao-e-sqlite"),
        pytest.param(TRIGGER, None, "estrutura", id="objeto-extra"),
        pytest.param(ORFAO, None, "chave estrangeira", id="referencia-orfa"),
        pytest.param(DESCONHECIDA, None, "9999", id="revisao-desconhecida-ou-mais-nova"),
    ],
)
def test_invalid_old_backup_is_refused_without_side_effects(
    tmp_path: Path,
    atual: Path,
    pasta_backups: Path,
    sql: str | None,
    estragar: Any,
    mensagem: str,
) -> None:
    arquivo = _backup_antigo(tmp_path, sql=sql)
    if estragar:
        estragar(arquivo)
    original = _estado(arquivo, caminho_manifesto(arquivo))
    banco = _estado(atual)

    with pytest.raises(RestauracaoRecusada, match=mensagem) as erro:
        migrar_backup(arquivo, pasta_backups)

    assert "Nada foi alterado" in str(erro.value)
    assert ANTIGO not in str(erro.value)
    assert _estado(arquivo, caminho_manifesto(arquivo)) == original
    assert _estado(atual) == banco
    assert _temporarios(pasta_backups) == [] and _migrados(pasta_backups) == []


def test_backup_older_than_anonymization_is_still_refused(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = tmp_path / "dados" / "salesos.db"
    migrar(db, "0002")
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', ?, 'site')", (ANTIGO,))
    conn.commit()
    conn.close()
    arquivo = criar_backup(db, tmp_path / "antigos")
    migrar(db)  # o banco atual evolui até o head e o cliente é anonimizado
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE clientes SET nome = 'Cliente anonimizado #1', anonimizado_em = CURRENT_TIMESTAMP"
    )
    conn.commit()
    conn.close()
    banco = _estado(db)

    migrado = migrar_backup(arquivo, pasta_backups)
    with pytest.raises(RestauracaoRecusada, match="anonimiza"):
        restaurar(db, migrado, pasta_backups)
    assert _estado(db) == banco
    assert _temporarios(pasta_backups) == []
    restaurar(db, migrado, pasta_backups, aceitar_reintroducao=True)
    assert nomes(db) == [ANTIGO]


@pytest.mark.parametrize("erro", [RuntimeError("falha injetada"), KeyboardInterrupt()])
def test_failure_during_migration_cleans_up_and_changes_nothing(
    tmp_path: Path,
    atual: Path,
    pasta_backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    erro: BaseException,
) -> None:
    arquivo = _backup_antigo(tmp_path)
    original = _estado(arquivo, caminho_manifesto(arquivo))
    banco = _estado(atual)

    def checagem_que_falha(_conexao: Any) -> None:
        raise erro

    # O env.py importa a checagem de FK a cada migração: a falha acontece no meio do upgrade.
    monkeypatch.setattr("salesos.db.check_foreign_keys", checagem_que_falha)
    with pytest.raises((RestauracaoRecusada, KeyboardInterrupt)):
        migrar_backup(arquivo, pasta_backups)

    assert _estado(arquivo, caminho_manifesto(arquivo)) == original
    assert _estado(atual) == banco
    assert _temporarios(pasta_backups) == [] and _migrados(pasta_backups) == []


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
        arquivo = _backup_antigo(tmp_path)
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
    arquivo = _backup_antigo(tmp_path)
    capfd.readouterr()
    _escutar(caplog)
    logging.getLogger("salesos.migracao_backup").debug("sonda do teste")
    restaurar(atual, migrar_backup(arquivo, pasta_backups), pasta_backups)
    saida = capfd.readouterr()
    assert "sonda do teste" in caplog.text  # a captura funciona: o teste não é vazio
    for texto in (caplog.text, saida.out, saida.err):
        assert ANTIGO.lower() not in texto.lower()


@pytest.mark.parametrize("revisao", revisoes_anteriores())
def test_every_previous_revision_can_be_migrated_and_restored(
    tmp_path: Path, atual: Path, pasta_backups: Path, revisao: str
) -> None:
    """Regressão: cada migração nova (0004 em diante) precisa manter este caminho funcionando."""
    arquivo = _backup_antigo(tmp_path, revisao)
    restaurar(atual, migrar_backup(arquivo, pasta_backups), pasta_backups)
    assert nomes(atual) == ([] if revisao == "0001" else [ANTIGO])


def test_chain_covers_every_revision_before_head() -> None:
    anteriores = revisoes_anteriores()
    assert anteriores[0] == "0001"
    assert revisao_atual() not in anteriores
    assert len(anteriores) >= 2  # 0001 e 0002 hoje; cresce a cada migração


def test_copy_that_differs_from_the_manifest_is_refused(
    tmp_path: Path, atual: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O arquivo pode mudar entre a verificação e a cópia: a cópia é conferida de novo."""
    arquivo = _backup_antigo(tmp_path)
    original = _estado(arquivo, caminho_manifesto(arquivo))
    copiar_real = shutil.copyfile

    def copiar_e_alterar(origem: Any, destino: Any) -> Any:
        resultado = copiar_real(origem, destino)
        _alterar_bytes(Path(destino))
        return resultado

    monkeypatch.setattr(shutil, "copyfile", copiar_e_alterar)
    with pytest.raises(RestauracaoRecusada, match="SHA-256"):
        migrar_backup(arquivo, pasta_backups)
    assert _estado(arquivo, caminho_manifesto(arquivo)) == original
    assert _temporarios(pasta_backups) == [] and _migrados(pasta_backups) == []


def test_unexpected_alembic_error_becomes_a_refusal(
    tmp_path: Path, atual: Path, pasta_backups: Path
) -> None:
    """Duas linhas em alembic_version: o Alembic falha com CommandError, que não pode escapar."""
    arquivo = _backup_antigo(tmp_path, sql="INSERT INTO alembic_version VALUES ('0001');")
    banco = _estado(atual)
    with pytest.raises(RestauracaoRecusada, match="Nada foi alterado"):
        migrar_backup(arquivo, pasta_backups)
    assert _estado(atual) == banco
    assert _temporarios(pasta_backups) == [] and _migrados(pasta_backups) == []


def test_backup_folder_with_percent_sign_works(tmp_path: Path, atual: Path) -> None:
    pasta = tmp_path / "backups 100% teste"
    restaurar(atual, migrar_backup(_backup_antigo(tmp_path), pasta), pasta)
    assert nomes(atual) == [ANTIGO]


def test_interruption_before_verification_leaves_no_unverified_migrated_backup(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = _backup_antigo(tmp_path)

    def verificacao_interrompida(*_a: Any, **_k: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "salesos.migracao_backup.verificar_backup",
        _primeira_real_depois(verificacao_interrompida),
    )
    with pytest.raises(KeyboardInterrupt):
        migrar_backup(arquivo, pasta_backups)
    assert _migrados(pasta_backups) == [] and _temporarios(pasta_backups) == []


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
    arquivo = _backup_antigo(tmp_path)
    _escutar(caplog)
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
    arquivo = _backup_antigo(tmp_path)
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
    assert _migrados(pasta_backups) == [] and _temporarios(pasta_backups) == []
