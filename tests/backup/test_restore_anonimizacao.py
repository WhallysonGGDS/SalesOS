"""Restauração e anonimização: reintrodução de dados só com consentimento explícito."""

import sqlite3
from pathlib import Path

import pytest

from salesos.backup import criar_backup
from salesos.restore import RestauracaoRecusada, restaurar
from tests.backup.conftest import criar_banco, nomes


def test_backup_older_than_anonymization_needs_explicit_consent(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Pessoa Ficticia")
    arquivo = criar_backup(db, pasta_backups)
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE clientes SET nome = 'Cliente anonimizado #1', anonimizado_em = CURRENT_TIMESTAMP"
    )
    conn.commit()
    conn.close()
    with pytest.raises(RestauracaoRecusada, match="anonimiza"):
        restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Cliente anonimizado #1"]
    restaurar(db, arquivo, pasta_backups, aceitar_reintroducao=True)
    assert nomes(db) == ["Pessoa Ficticia"]


def _anonimizar_sql(db: Path, cliente_id: int) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE clientes SET nome = 'Cliente anonimizado #' || id, "
        "anonimizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        (cliente_id,),
    )
    conn.commit()
    conn.close()


def _novo_cliente_sql(db: Path, nome: str) -> int:
    conn = sqlite3.connect(db)
    cursor = conn.execute(
        "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', ?, 'site')", (nome,)
    )
    conn.commit()
    conn.close()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def test_client_created_and_anonymized_after_backup_is_not_a_reintroduction(
    tmp_path: Path, pasta_backups: Path
) -> None:
    """Quem nem existe no backup não pode voltar com a restauração (sem falso alerta)."""
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Pessoa Antiga")
    arquivo = criar_backup(db, pasta_backups)
    _anonimizar_sql(db, _novo_cliente_sql(db, "Pessoa Nova Ficticia"))
    restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Pessoa Antiga"]


def test_already_anonymized_in_backup_is_not_a_reintroduction(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Pessoa Ficticia")
    _anonimizar_sql(db, 1)
    arquivo = criar_backup(db, pasta_backups)
    restaurar(db, arquivo, pasta_backups)
    assert nomes(db) == ["Cliente anonimizado #1"]


def test_real_reintroduction_is_still_refused_among_new_clients(
    tmp_path: Path, pasta_backups: Path
) -> None:
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Pessoa No Backup")
    arquivo = criar_backup(db, pasta_backups)
    _anonimizar_sql(db, 1)
    _anonimizar_sql(db, _novo_cliente_sql(db, "Pessoa Nova Ficticia"))
    with pytest.raises(RestauracaoRecusada, match=r"anonimização de 1 cliente\(s\)"):
        restaurar(db, arquivo, pasta_backups)
