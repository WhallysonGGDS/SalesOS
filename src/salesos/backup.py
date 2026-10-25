"""Backup do SQLite com verificação de integridade e SHA-256 (Fase 02, E4).

O backup usa a API de backup do SQLite: a cópia é consistente mesmo com o servidor ligado.
Nunca sobrescreve um arquivo e nunca apaga backups (D7). O manifesto guarda só o nome do
arquivo, o hash, a revisão do esquema, o tamanho e a data: nenhum dado pessoal.
"""

import functools
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from salesos.db import restringir

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


ESPERA_BLOQUEIO = 10.0  # segundos que o backup espera outro programa liberar o banco


class BackupInvalido(ValueError):
    pass


class BancoEmUso(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "O banco está bloqueado por outro programa (DB Browser ou outro). "
            "Feche-o e tente de novo. Nada foi alterado."
        )


def bloqueado(erro: sqlite3.Error) -> bool:
    """SQLITE_BUSY ou SQLITE_LOCKED, inclusive os códigos estendidos (byte baixo)."""
    codigo = getattr(erro, "sqlite_errorcode", None)
    return codigo is not None and codigo & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)


def carimbo() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def caminho_manifesto(arquivo: Path) -> Path:
    return arquivo.with_name(arquivo.name + ".json")


def revisao_atual() -> str | None:
    return ScriptDirectory(str(MIGRATIONS)).get_current_head()


def sha256_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            resumo.update(bloco)
    return resumo.hexdigest()


def sincronizar(caminho: Path) -> None:
    """Grava no disco o arquivo (ou, fora do Windows, a entrada da pasta)."""
    if caminho.is_dir():
        if sys.platform == "win32":
            return  # o Windows não abre pastas para fsync
        fd = os.open(caminho, os.O_RDONLY)
    else:
        fd = os.open(caminho, os.O_RDWR)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def abrir_leitura(caminho: Path) -> sqlite3.Connection:
    """Somente leitura: não cria arquivo e não altera o banco.

    `trusted_schema=OFF`: funções com efeito colateral não rodam a partir de views ou triggers
    de um arquivo que veio de fora.
    """
    conn = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True)
    conn.execute("PRAGMA trusted_schema=OFF")
    return conn


def _estrutura(conn: sqlite3.Connection) -> frozenset[tuple[Any, ...]]:
    """Objetos do esquema (tabelas, índices, views, triggers) e as colunas de cada tabela.

    O texto SQL não entra: o mesmo esquema legítimo pode ter texto diferente conforme o
    caminho de migração. Nomes `sqlite_*` também entram: um arquivo forjado com
    `writable_schema` pode usá-los para esconder objetos.
    """
    itens: set[tuple[Any, ...]] = set()
    objetos = conn.execute("SELECT type, name, tbl_name FROM sqlite_master").fetchall()
    for tipo, nome, tabela in objetos:
        itens.add((tipo, nome, tabela))
        if tipo == "table":
            identificador = '"' + nome.replace('"', '""') + '"'
            for coluna in conn.execute(f"PRAGMA table_xinfo({identificador})"):
                itens.add(("coluna", nome, *coluna[1:]))
    return frozenset(itens)


@functools.cache
def estrutura_esperada() -> frozenset[tuple[Any, ...]]:
    """Esquema do head, obtido rodando as migrações reais num banco temporário."""
    with tempfile.TemporaryDirectory() as pasta:
        referencia = Path(pasta) / "referencia.db"
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{referencia}")
        command.upgrade(config, "head")
        conn = abrir_leitura(referencia)
        try:
            return _estrutura(conn)
        finally:
            conn.close()


def verificar_integridade(caminho: Path) -> str:
    """Roda `integrity_check` e devolve a revisão do esquema gravada no banco."""
    try:
        conn = abrir_leitura(caminho)
        try:
            resultado = conn.execute("PRAGMA integrity_check").fetchall()
            if resultado != [("ok",)]:
                raise BackupInvalido("falha de integridade do SQLite")
            linha = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as erro:
        raise BackupInvalido(f"falha de integridade do SQLite: {erro}") from erro
    if linha is None:
        raise BackupInvalido("banco sem revisão do esquema")
    return str(linha[0])


def _copiar_sqlite(origem: Path, destino: Path) -> None:
    # mode=rw: se o banco não existir, falha em vez de criar um arquivo vazio no lugar.
    fonte = sqlite3.connect(f"{origem.resolve().as_uri()}?mode=rw", uri=True)
    alvo = sqlite3.connect(destino)
    prazo = time.monotonic() + ESPERA_BLOQUEIO

    def desistir_se_preso(status: int, _restantes: int, _total: int) -> None:
        # Sem isso, `Connection.backup` repete o passo bloqueado para sempre.
        if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) and time.monotonic() > prazo:
            raise BancoEmUso

    try:
        try:
            fonte.backup(alvo, progress=desistir_se_preso)
        except sqlite3.OperationalError as erro:
            if bloqueado(erro):
                raise BancoEmUso from erro
            raise
        # Modo DELETE: o arquivo fica completo sozinho, sem `-wal`, e o hash não muda ao abrir.
        alvo.execute("PRAGMA journal_mode=DELETE")
    finally:
        alvo.close()
        fonte.close()


def _publicar(temporario: Path, final: Path) -> None:
    """Move sem sobrescrever: falha com FileExistsError se o destino já existir."""
    if sys.platform == "win32":
        os.rename(temporario, final)  # no Windows, rename nunca sobrescreve
    else:
        os.link(temporario, final)  # no POSIX, rename sobrescreveria; link não
        temporario.unlink()


def criar_backup(db: Path, pasta: Path, prefixo: str = "salesos") -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    restringir(pasta, 0o700)
    final = pasta / f"{prefixo}-{carimbo()}.db"
    manifesto = caminho_manifesto(final)
    temporario = final.with_name(final.name + ".tmp")
    manifesto_tmp = manifesto.with_name(manifesto.name + ".tmp")
    if final.exists() or manifesto.exists():
        raise FileExistsError(f"backup já existe: {final.name}")
    publicado = False
    try:
        _copiar_sqlite(db, temporario)
        restringir(temporario)
        sincronizar(temporario)
        dados = {
            "arquivo": final.name,
            "sha256": sha256_arquivo(temporario),
            "revisao": verificar_integridade(temporario),
            "tamanho": temporario.stat().st_size,
            "criado_em": datetime.now(UTC).isoformat(),
        }
        manifesto_tmp.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        restringir(manifesto_tmp)
        sincronizar(manifesto_tmp)
        _publicar(temporario, final)
        publicado = True
        _publicar(manifesto_tmp, manifesto)
        sincronizar(pasta)
    except BaseException:
        if publicado and not manifesto.exists():
            final.unlink()  # backup sem manifesto seria recusado; é nosso e incompleto
        raise
    finally:
        temporario.unlink(missing_ok=True)
        manifesto_tmp.unlink(missing_ok=True)
    return final


def verificar_backup(
    arquivo: Path, manifesto_de: Path | None = None, exigir_revisao: bool = True
) -> dict[str, Any]:
    """Confere manifesto, SHA-256, integridade e revisão. `manifesto_de` serve para cópias."""
    manifesto = caminho_manifesto(manifesto_de or arquivo)
    try:
        dados: dict[str, Any] = json.loads(manifesto.read_text(encoding="utf-8"))
    except FileNotFoundError as erro:
        raise BackupInvalido("manifesto do backup ausente") from erro
    except (OSError, ValueError) as erro:
        raise BackupInvalido("manifesto do backup ilegível") from erro
    if not isinstance(dados, dict) or sha256_arquivo(arquivo) != dados.get("sha256"):
        raise BackupInvalido("SHA-256 do arquivo diverge do manifesto")
    revisao = verificar_integridade(arquivo)
    if exigir_revisao:
        if revisao != revisao_atual():
            raise BackupInvalido(f"revisão do esquema {revisao} difere da atual {revisao_atual()}")
        conn = abrir_leitura(arquivo)
        try:
            diferentes = _estrutura(conn) ^ estrutura_esperada()
        finally:
            conn.close()
        if diferentes:
            # Só a quantidade: nomes de objetos de um arquivo de fora não vão para mensagens.
            raise BackupInvalido(
                f"estrutura do banco diferente da esperada ({len(diferentes)} diferença(s): "
                "tabelas, colunas, índices, views ou triggers)"
            )
    return dados
