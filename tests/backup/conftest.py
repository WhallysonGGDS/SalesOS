import hashlib
import logging
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


# --- B1: backups de revisão anterior (restore --migrar) ---

ANTIGO = "Qwxclienteantigo"


def backup_antigo(base: Path, revisao: str = "0002", sql: str | None = None) -> Path:
    """Banco fictício parado na `revisao`, com um cliente, e o backup verificado dele."""
    db = base / f"antigo-{revisao}" / "salesos.db"
    migrar(db, revisao)
    conn = sqlite3.connect(db)
    if revisao != "0001":  # a linha de base não tem tabelas de negócio
        conn.execute(
            "INSERT INTO clientes (tipo, nome, origem) VALUES ('PJ', ?, 'site')", (ANTIGO,)
        )
    tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "oportunidades" in tabelas:  # da Fase 03 em diante: dados também nas tabelas novas
        conn.execute(
            "INSERT INTO oportunidades (cliente_id, titulo, etapa) VALUES (1, 'Projeto', 'novo_lead')"
        )
    if sql:
        conn.executescript(sql)
    conn.commit()
    conn.close()
    return criar_backup(db, base / f"antigo-{revisao}" / "backups")


def escutar(caplog: pytest.LogCaptureFixture) -> None:
    """O `migrar()` dos testes usa o alembic.ini, cujo fileConfig tira o handler do caplog."""
    raiz = logging.getLogger()
    if caplog.handler not in raiz.handlers:
        raiz.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)


def estado(*arquivos: Path) -> list[tuple[str, int]]:
    return [(sha(a), a.stat().st_mtime_ns) for a in arquivos]


def temporarios(pasta: Path) -> list[str]:
    return sorted(p.name for p in pasta.glob(".migracao-*")) if pasta.exists() else []


def migrados(pasta: Path) -> list[str]:
    return sorted(p.name for p in pasta.glob("migrado-*")) if pasta.exists() else []


@pytest.fixture
def atual(tmp_path: Path) -> Path:
    return criar_banco(tmp_path / "dados" / "salesos.db", "Atual")


def alterar_bytes(arquivo: Path) -> None:
    with arquivo.open("r+b") as f:
        f.seek(5000)
        f.write(b"X")
