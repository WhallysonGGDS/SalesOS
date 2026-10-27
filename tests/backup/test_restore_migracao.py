"""B1: `restore --migrar` migra uma cópia temporária de um backup antigo (dados fictícios)."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from salesos.backup import caminho_manifesto, criar_backup, revisao_atual, verificar_backup
from salesos.migracao_backup import migrar_backup, revisoes_anteriores
from salesos.restore import RestauracaoRecusada, restaurar
from tests.backup.conftest import (
    ANTIGO,
    alterar_bytes,
    backup_antigo,
    criar_banco,
    estado,
    migrados,
    nomes,
    sha,
    temporarios,
)
from tests.conftest import migrar


def test_valid_old_backup_is_migrated_and_restored(
    tmp_path: Path, atual: Path, pasta_backups: Path
) -> None:
    arquivo = backup_antigo(tmp_path)
    original = estado(arquivo, caminho_manifesto(arquivo))
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
    assert estado(arquivo, caminho_manifesto(arquivo)) == original
    assert temporarios(pasta_backups) == []


def test_backup_already_at_current_revision_needs_no_migration(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "outro" / "salesos.db", "Ja atual")
    arquivo = criar_backup(db, tmp_path / "outro" / "backups")
    assert migrar_backup(arquivo, pasta_backups) == arquivo
    assert migrados(pasta_backups) == [] and temporarios(pasta_backups) == []


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
        pytest.param(None, alterar_bytes, "SHA-256", id="alterado-depois-do-manifesto"),
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
    arquivo = backup_antigo(tmp_path, sql=sql)
    if estragar:
        estragar(arquivo)
    original = estado(arquivo, caminho_manifesto(arquivo))
    banco = estado(atual)

    with pytest.raises(RestauracaoRecusada, match=mensagem) as erro:
        migrar_backup(arquivo, pasta_backups)

    assert "Nada foi alterado" in str(erro.value)
    assert ANTIGO not in str(erro.value)
    assert estado(arquivo, caminho_manifesto(arquivo)) == original
    assert estado(atual) == banco
    assert temporarios(pasta_backups) == [] and migrados(pasta_backups) == []


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
    banco = estado(db)

    migrado = migrar_backup(arquivo, pasta_backups)
    with pytest.raises(RestauracaoRecusada, match="anonimiza"):
        restaurar(db, migrado, pasta_backups)
    assert estado(db) == banco
    assert temporarios(pasta_backups) == []
    restaurar(db, migrado, pasta_backups, aceitar_reintroducao=True)
    assert nomes(db) == [ANTIGO]


@pytest.mark.parametrize("revisao", revisoes_anteriores())
def test_every_previous_revision_can_be_migrated_and_restored(
    tmp_path: Path, atual: Path, pasta_backups: Path, revisao: str
) -> None:
    """Regressão: cada migração nova (0004 em diante) precisa manter este caminho funcionando."""
    arquivo = backup_antigo(tmp_path, revisao)
    restaurar(atual, migrar_backup(arquivo, pasta_backups), pasta_backups)
    assert nomes(atual) == ([] if revisao == "0001" else [ANTIGO])


def test_chain_covers_every_revision_before_head() -> None:
    anteriores = revisoes_anteriores()
    assert anteriores[0] == "0001"
    assert revisao_atual() not in anteriores
    assert len(anteriores) >= 2  # 0001 e 0002 hoje; cresce a cada migração
