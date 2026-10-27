"""Backup consistente, verificado por integridade e SHA-256 (dados fictícios)."""

import errno
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from salesos import backup
from salesos.backup import BackupInvalido, criar_backup, verificar_backup
from tests.backup.conftest import criar_banco, nomes
from tests.conftest import migrar

SENTINELA = "Qwxbackupsentinela"


def test_backup_has_verified_manifest_without_personal_data(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "salesos.db", SENTINELA)
    arquivo = criar_backup(db, pasta_backups)
    manifesto_txt = arquivo.with_name(arquivo.name + ".json").read_text(encoding="utf-8")
    manifesto = json.loads(manifesto_txt)
    assert manifesto["sha256"] == hashlib.sha256(arquivo.read_bytes()).hexdigest()
    assert manifesto["revisao"] == "0004"
    assert SENTINELA.lower() not in manifesto_txt.lower()
    assert verificar_backup(arquivo)["sha256"] == manifesto["sha256"]
    assert nomes(arquivo) == [SENTINELA]


def test_backup_is_consistent_while_a_writer_holds_a_transaction(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "salesos.db", "Confirmado")
    escritor = sqlite3.connect(db, isolation_level=None)
    escritor.execute("BEGIN IMMEDIATE")
    escritor.execute("INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', 'Pendente', 'site')")
    try:
        arquivo = criar_backup(db, pasta_backups)
    finally:
        escritor.execute("ROLLBACK")
        escritor.close()
    assert nomes(arquivo) == ["Confirmado"]
    verificar_backup(arquivo)


def test_backup_never_overwrites(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = criar_banco(tmp_path / "salesos.db", "A")
    monkeypatch.setattr(backup, "carimbo", lambda: "20261024T000000000000Z")
    primeiro = criar_backup(db, pasta_backups)
    antes = primeiro.read_bytes()
    with pytest.raises(FileExistsError):
        criar_backup(db, pasta_backups)
    assert primeiro.read_bytes() == antes
    assert sorted(p.name for p in pasta_backups.iterdir()) == [
        primeiro.name,
        primeiro.name + ".json",
    ]


def test_disk_full_leaves_no_partial_files(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = criar_banco(tmp_path / "salesos.db", "A")

    def disco_cheio(_origem: Path, destino: Path) -> None:
        destino.write_bytes(b"parcial")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(backup, "_copiar_sqlite", disco_cheio)
    with pytest.raises(OSError, match="space"):
        criar_backup(db, pasta_backups)
    assert list(pasta_backups.iterdir()) == []


def _regravar_manifesto(arquivo: Path, **campos: str) -> None:
    caminho = arquivo.with_name(arquivo.name + ".json")
    caminho.write_text(json.dumps(json.loads(caminho.read_text()) | campos), encoding="utf-8")


def test_hash_mismatch_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    _regravar_manifesto(arquivo, sha256="0" * 64)
    with pytest.raises(BackupInvalido, match="SHA-256"):
        verificar_backup(arquivo)


def test_corrupted_file_with_matching_hash_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    conn = sqlite3.connect(arquivo)
    (raiz,) = conn.execute("SELECT rootpage FROM sqlite_master WHERE name = 'clientes'").fetchone()
    conn.close()
    dados = bytearray(arquivo.read_bytes())
    tamanho = int.from_bytes(dados[16:18], "big")
    # Só a página dos clientes: o resto do arquivo (inclusive a revisão) continua legível.
    dados[(raiz - 1) * tamanho : raiz * tamanho] = b"\xff" * tamanho
    arquivo.write_bytes(bytes(dados))
    _regravar_manifesto(arquivo, sha256=hashlib.sha256(dados).hexdigest())
    with pytest.raises(BackupInvalido, match="integridade"):
        verificar_backup(arquivo)


def test_non_database_file_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    arquivo.write_bytes(b"isto nao e um banco")
    _regravar_manifesto(arquivo, sha256=hashlib.sha256(b"isto nao e um banco").hexdigest())
    with pytest.raises(BackupInvalido, match="integridade"):
        verificar_backup(arquivo)


def test_missing_manifest_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    arquivo.with_name(arquivo.name + ".json").unlink()
    with pytest.raises(BackupInvalido, match="manifesto"):
        verificar_backup(arquivo)


def test_backup_from_other_schema_revision_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    antigo = tmp_path / "antigo.db"
    migrar(antigo, "0001")
    arquivo = criar_backup(antigo, pasta_backups)
    with pytest.raises(BackupInvalido, match="revisão"):
        verificar_backup(arquivo)


ESTRUTURAS_ESTRANHAS = {
    "trigger": (
        "CREATE TABLE copia (nome TEXT); CREATE TRIGGER espiao BEFORE UPDATE ON clientes "
        "BEGIN INSERT INTO copia VALUES (old.nome); END;"
    ),
    "tabela": "CREATE TABLE extra (x TEXT);",
    "view": "CREATE VIEW resumo AS SELECT nome, email FROM clientes;",
    "coluna": "ALTER TABLE clientes ADD COLUMN apelido TEXT;",
    "indice": "CREATE INDEX ix_extra ON clientes (email);",
    # Mesmo nome, outras colunas: só a lista de colunas do índice denuncia.
    "indice_colunas": (
        "DROP INDEX ix_tarefas_estado_prazo; "
        "CREATE INDEX ix_tarefas_estado_prazo ON tarefas (prazo);"
    ),
}


@pytest.mark.parametrize("sql", ESTRUTURAS_ESTRANHAS.values(), ids=ESTRUTURAS_ESTRANHAS.keys())
def test_backup_with_unexpected_schema_is_refused(
    tmp_path: Path, pasta_backups: Path, sql: str
) -> None:
    """Um arquivo forjado com objetos extras poderia guardar dados depois da anonimização."""
    db = criar_banco(tmp_path / "salesos.db", "A")
    conn = sqlite3.connect(db)
    conn.executescript(sql)
    conn.close()
    arquivo = criar_backup(db, pasta_backups)  # o hash bate: só a estrutura denuncia
    with pytest.raises(BackupInvalido, match="estrutura"):
        verificar_backup(arquivo)


# Restrições não se alteram com ALTER TABLE no SQLite: um arquivo forjado reescreve o SQL da
# tabela com `writable_schema`. (tabela, trecho original, trecho forjado). Os casos de CHECK
# aguardam a decisão sobre como compará-los (ADR 0005).
REESCRITAS = {
    "fk_cascade": (
        "tarefas",
        "REFERENCES clientes (id) ON DELETE RESTRICT",
        "REFERENCES clientes (id) ON DELETE CASCADE",
    ),
    "fk_removida": (
        "tarefas",
        ", \n\tCONSTRAINT fk_tarefas_oportunidade_id_oportunidades FOREIGN KEY(oportunidade_id) "
        "REFERENCES oportunidades (id) ON DELETE RESTRICT",
        "",
    ),
}


@pytest.mark.parametrize("reescrita", REESCRITAS.values(), ids=REESCRITAS.keys())
def test_backup_with_rewritten_constraints_is_refused(
    tmp_path: Path, pasta_backups: Path, reescrita: tuple[str, str, str]
) -> None:
    tabela, de, para = reescrita
    db = criar_banco(tmp_path / "salesos.db", "A")
    conn = sqlite3.connect(db)
    (sql,) = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (tabela,)).fetchone()
    assert sql.count(de) == 1  # a forja precisa acertar o texto real
    versao = conn.execute("PRAGMA schema_version").fetchone()[0]
    conn.execute("PRAGMA writable_schema = ON")
    conn.execute("UPDATE sqlite_master SET sql = ? WHERE name = ?", (sql.replace(de, para), tabela))
    conn.execute(f"PRAGMA schema_version = {versao + 1}")
    conn.commit()
    conn.close()
    arquivo = criar_backup(db, pasta_backups)  # o hash bate: só a estrutura denuncia
    with pytest.raises(BackupInvalido, match="estrutura"):
        verificar_backup(arquivo)


def test_legitimate_schema_is_accepted_and_files_open_with_untrusted_schema(
    tmp_path: Path, pasta_backups: Path
) -> None:
    arquivo = criar_backup(criar_banco(tmp_path / "salesos.db", "A"), pasta_backups)
    verificar_backup(arquivo)
    conn = backup.abrir_leitura(arquivo)
    try:
        assert conn.execute("PRAGMA trusted_schema").fetchone() == (0,)
    finally:
        conn.close()


def test_object_hidden_behind_internal_name_is_refused(tmp_path: Path, pasta_backups: Path) -> None:
    """Com writable_schema, um arquivo forjado pode dar nome `sqlite_*` a um trigger."""
    db = criar_banco(tmp_path / "salesos.db", "A")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE copia (nome TEXT)")
    conn.execute(
        "CREATE TRIGGER t BEFORE UPDATE ON clientes BEGIN INSERT INTO copia VALUES (old.nome); END"
    )
    conn.execute("DROP TABLE copia")  # só o trigger fica como objeto extra
    conn.execute("PRAGMA writable_schema=ON")
    conn.execute("UPDATE sqlite_master SET name = 'sqlite_oculto' WHERE type = 'trigger'")
    conn.commit()
    conn.close()
    # Forjado à mão (a API de backup nem abre esse arquivo), com manifesto coerente.
    pasta_backups.mkdir()
    arquivo = pasta_backups / "forjado.db"
    arquivo.write_bytes(db.read_bytes())
    sha = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    manifesto = {"sha256": sha, "revisao": "0004"}
    arquivo.with_name(arquivo.name + ".json").write_text(json.dumps(manifesto), encoding="utf-8")
    with pytest.raises(BackupInvalido):
        verificar_backup(arquivo)


def test_backup_gives_up_with_clear_message_when_database_is_locked_exclusively(
    tmp_path: Path, pasta_backups: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem prazo, o laço de `Connection.backup` repetiria o passo bloqueado para sempre."""
    db = criar_banco(tmp_path / "salesos.db", "Atual")
    monkeypatch.setattr(backup, "ESPERA_BLOQUEIO", 0.2)
    dono = sqlite3.connect(db, isolation_level=None)
    dono.execute("PRAGMA locking_mode=EXCLUSIVE")
    dono.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(backup.BancoEmUso, match="bloqueado por outro programa"):
            criar_backup(db, pasta_backups)
    finally:
        dono.rollback()
        dono.close()
    assert list(pasta_backups.iterdir()) == []  # nenhum temporário nem backup parcial


def _erro_sqlite(codigo: int) -> sqlite3.OperationalError:
    erro = sqlite3.OperationalError("simulado")
    erro.sqlite_errorcode = codigo
    return erro


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        pytest.param(5, True, id="SQLITE_BUSY"),
        pytest.param(6, True, id="SQLITE_LOCKED"),
        pytest.param(517, True, id="SQLITE_BUSY_SNAPSHOT"),
        pytest.param(262, True, id="SQLITE_LOCKED_SHAREDCACHE"),
        pytest.param(1, False, id="SQLITE_ERROR"),
        pytest.param(8, False, id="SQLITE_READONLY"),
        pytest.param(10, False, id="SQLITE_IOERR"),
        pytest.param(14, False, id="SQLITE_CANTOPEN"),
        pytest.param(13, False, id="SQLITE_FULL"),
    ],
)
def test_locked_is_told_apart_from_other_sqlite_errors(codigo: int, esperado: bool) -> None:
    assert backup.bloqueado(_erro_sqlite(codigo)) is esperado


def test_error_without_sqlite_code_is_not_a_lock() -> None:
    assert backup.bloqueado(sqlite3.OperationalError("sem código")) is False
