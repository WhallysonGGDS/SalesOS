"""E3: backup com dados que violam as regras do banco é recusado antes da troca.

Em modo só leitura, o `integrity_check` do SQLite não confere CHECKs, e nada rodava
`foreign_key_check`. Bancos temporários com dados fictícios.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from salesos.backup import criar_backup, sha256_arquivo
from salesos.migracao_backup import PREFIXO_TEMPORARIO, migrar_backup
from salesos.restore import RestauracaoRecusada, controle_pendente, restaurar
from tests.backup.conftest import criar_banco
from tests.conftest import migrar

NOME_SENTINELA = "Qwxdadosentinela"  # o mesmo texto vai literal no SQL abaixo

# Linhas que o SQLite só aceita com as proteções desligadas na conexão de quem forja.
VIOLACOES = {
    "check": (
        "PRAGMA ignore_check_constraints = ON; INSERT INTO clientes (tipo, nome, origem, busca) "
        "VALUES ('XX', 'Qwxdadosentinela', 'site', 'x');",
        "CHECK",
    ),
    "chave_orfa": (
        "PRAGMA foreign_keys = OFF; "
        "INSERT INTO contatos (cliente_id, nome) VALUES (999, 'Qwxdadosentinela');",
        "chave estrangeira",
    ),
}


def _forjar(db: Path, sql: str) -> None:
    conn = sqlite3.connect(db)
    conn.executescript(sql)
    conn.commit()
    conn.close()


def _sem_sobras(db: Path, pasta_backups: Path) -> None:
    assert not list(db.parent.glob(f"{db.name}.staging-*"))
    assert not list(pasta_backups.glob(f"{PREFIXO_TEMPORARIO}*"))
    assert not controle_pendente(db)


@pytest.mark.parametrize("violacao", VIOLACOES.values(), ids=VIOLACOES.keys())
def test_restore_refuses_backup_with_invalid_data(
    tmp_path: Path, violacao: tuple[str, str]
) -> None:
    sql, motivo = violacao
    pasta = tmp_path / "backups"
    origem = criar_banco(tmp_path / "origem.db", "Antigo")
    _forjar(origem, sql)
    backup = criar_backup(origem, pasta)  # manifesto e SHA-256 batem: só os dados denunciam
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    antes_db, antes_backup = sha256_arquivo(db), sha256_arquivo(backup)
    with pytest.raises(RestauracaoRecusada, match=motivo) as erro:
        restaurar(db, backup, pasta)
    assert NOME_SENTINELA not in str(erro.value)
    assert (sha256_arquivo(db), sha256_arquivo(backup)) == (antes_db, antes_backup)
    _sem_sobras(db, pasta)


@pytest.mark.parametrize("violacao", VIOLACOES.values(), ids=VIOLACOES.keys())
def test_migrate_flow_refuses_old_backup_with_invalid_data(
    tmp_path: Path, violacao: tuple[str, str]
) -> None:
    sql, _motivo = violacao
    pasta = tmp_path / "backups"
    antigo = tmp_path / "antigo.db"
    migrar(antigo, "0002")
    _forjar(antigo, sql)
    backup = criar_backup(antigo, pasta)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    antes_db, antes_backup = sha256_arquivo(db), sha256_arquivo(backup)
    # A recusa pode vir da migração da cópia (chave órfã) ou da restauração (CHECK).
    with pytest.raises(RestauracaoRecusada) as erro:
        restaurar(db, migrar_backup(backup, pasta), pasta)
    assert NOME_SENTINELA not in str(erro.value)
    assert (sha256_arquivo(db), sha256_arquivo(backup)) == (antes_db, antes_backup)
    _sem_sobras(db, pasta)


def test_legitimate_backup_is_still_restored_and_left_byte_identical(tmp_path: Path) -> None:
    pasta = tmp_path / "backups"
    backup = criar_backup(criar_banco(tmp_path / "origem.db", "Antigo"), pasta)
    antes_backup = sha256_arquivo(backup)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    restaurar(db, backup, pasta)
    # A cópia privada não pode mudar um byte com a checagem: logo depois da troca, o
    # `restaurar` confere o SHA-256 dela contra o manifesto (e falharia aqui).
    assert sha256_arquivo(backup) == antes_backup
    _sem_sobras(db, pasta)


def test_backup_with_wal_header_is_refused_without_leftovers(tmp_path: Path) -> None:
    # `criar_backup` sempre grava em modo DELETE; um cabeçalho WAL faria o SQLite criar
    # `-wal`/`-shm` ao lado da cópia privada, na pasta dos dados.
    pasta = tmp_path / "backups"
    origem = criar_banco(tmp_path / "origem.db", "Antigo")
    backup = criar_backup(origem, pasta)
    conteudo = bytearray(backup.read_bytes())
    conteudo[18:20] = b"\x02\x02"  # versões de escrita e leitura: 2 = WAL
    backup.write_bytes(bytes(conteudo))
    manifesto = backup.with_name(backup.name + ".json")
    registro = json.loads(manifesto.read_text())
    registro["sha256"] = sha256_arquivo(backup)  # o hash bate: só o cabeçalho denuncia
    manifesto.write_text(json.dumps(registro))
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    antes = sha256_arquivo(db)
    with pytest.raises(RestauracaoRecusada, match="modo de diário"):
        restaurar(db, backup, pasta)
    assert sha256_arquivo(db) == antes
    sobras = [p.name for p in db.parent.iterdir() if p.name.endswith(("-wal", "-shm"))]
    assert [s for s in sobras if "staging" in s] == []
    _sem_sobras(db, pasta)
