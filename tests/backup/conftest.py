import sqlite3
from pathlib import Path

import pytest

from tests.conftest import migrar


def criar_banco(db: Path, *nomes: str) -> Path:
    """Banco migrado com clientes fictícios, em modo WAL como o da aplicação."""
    migrar(db)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executemany(
        "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', ?, 'site')", [(n,) for n in nomes]
    )
    conn.commit()
    conn.close()
    return db


def _ler(db: Path) -> sqlite3.Connection:
    """Só leitura: nunca cria um banco vazio onde não há arquivo."""
    return sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)


def nomes(db: Path) -> list[str]:
    conn = _ler(db)
    try:
        return [r[0] for r in conn.execute("SELECT nome FROM clientes ORDER BY id")]
    finally:
        conn.close()


def modo(db: Path) -> str:
    conn = _ler(db)
    try:
        return str(conn.execute("PRAGMA journal_mode").fetchone()[0])
    finally:
        conn.close()


@pytest.fixture
def pasta_backups(tmp_path: Path) -> Path:
    return tmp_path / "backups"
