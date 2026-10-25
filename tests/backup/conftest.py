import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from salesos import restore
from salesos.backup import criar_backup
from salesos.restore import controle_pendente
from tests.conftest import migrar

ESTADOS_DESFEITOS = ["validating", "quiesced", "safety_backed_up", "original_moved", "swapped"]


class Queda(BaseException):
    """Simula o processo morrendo: nenhum `except Exception` roda."""


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


def sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@pytest.fixture
def cenario(tmp_path: Path, pasta_backups: Path) -> tuple[Path, Path]:
    """Banco "atual" e um backup verificado de outro banco ("Do backup")."""
    origem = criar_banco(tmp_path / "origem" / "salesos.db", "Do backup")
    arquivo = criar_backup(origem, pasta_backups)
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    return db, arquivo


def sobras(db: Path) -> list[str]:
    return sorted(p.name for p in db.parent.iterdir() if ".staging" in p.name)


def assert_original_intacto(db: Path) -> None:
    assert nomes(db) == ["Atual"]
    assert modo(db) == "wal"
    assert controle_pendente(db) is None
    assert sobras(db) == []


def falhar_no_estado(monkeypatch: pytest.MonkeyPatch, alvo: str, erro: BaseException) -> None:
    original = restore._gravar_estado

    def gravar(controle: Path, dados: dict[str, Any], estado: str) -> None:
        original(controle, dados, estado)
        if estado == alvo:
            raise erro

    monkeypatch.setattr(restore, "_gravar_estado", gravar)
