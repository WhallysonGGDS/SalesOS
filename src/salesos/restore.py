"""Restauração do SQLite com diário de estados e recuperação idempotente (Fase 02, E4).

Invariantes:
1. Em todo momento existe o original intacto (no lugar ou como `.pre-restore-<ts>`) ou um
   backup de segurança verificado.
2. A recuperação é idempotente e nunca apaga backups, originais nem o banco que falhou.
3. Cada mudança de estado é gravada e sincronizada no disco antes da ação seguinte.

Limite conhecido: no Linux, um programa que abrir o banco depois da sondagem não impede a
troca; ele continua com o arquivo antigo, preservado como `.pre-restore-<ts>`.
"""

import json
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from salesos.backup import (
    BackupInvalido,
    abrir_leitura,
    carimbo,
    criar_backup,
    sincronizar,
    verificar_backup,
)
from salesos.lock import caminho_trava, trava

logger = logging.getLogger(__name__)

TENTATIVAS_EXTRAS = 5
FECHE_OS_PROGRAMAS = (
    "Feche os programas que usam o banco (servidor do SalesOS, DB Browser ou outros) "
    "e tente de novo. Nada foi alterado."
)


class RestauracaoRecusada(RuntimeError):
    pass


@dataclass(frozen=True)
class Recuperacao:
    estado: str | None
    residuos: list[Path]


def caminho_controle(db: Path) -> Path:
    return db.with_name(db.name + ".restore.json")


def controle_pendente(db: Path) -> Path | None:
    controle = caminho_controle(db)
    return controle if controle.exists() else None


def _gravar_estado(controle: Path, dados: dict[str, Any], estado: str) -> None:
    dados["estado"] = estado
    temporario = controle.with_name(controle.name + ".tmp")
    temporario.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    sincronizar(temporario)
    os.replace(temporario, controle)
    sincronizar(controle.parent)


def _arquivar(controle: Path, dados: dict[str, Any], resultado: str) -> None:
    """O diário nunca é apagado: vira um registro com o resultado no nome."""
    destino = controle.with_name(
        f"{Path(dados['banco']).name}.restore-{dados['carimbo']}-{resultado}.json"
    )
    os.replace(controle, destino)
    sincronizar(controle.parent)


def _copiar(origem: Path, destino: Path) -> None:
    shutil.copyfile(origem, destino)
    sincronizar(destino)


def _mover(origem: Path, destino: Path) -> None:
    """`os.replace` com novas tentativas: no Windows, falha enquanto alguém usa o arquivo."""
    for tentativa in range(TENTATIVAS_EXTRAS + 1):
        try:
            os.replace(origem, destino)
            sincronizar(destino.parent)
            return
        except PermissionError:
            if tentativa == TENTATIVAS_EXTRAS:
                raise
            time.sleep(0.2 * 2**tentativa)


def _aquietar(db: Path) -> None:
    """Prova que ninguém usa o banco e tira-o do WAL, deixando um arquivo único e completo.

    `BEGIN IMMEDIATE` detecta escritores; o checkpoint incompleto detecta leitores; a saída
    do WAL falha com qualquer conexão aberta, inclusive ociosa. Nenhuma espera: falha na hora.
    """
    try:
        conn = sqlite3.connect(f"{db.resolve().as_uri()}?mode=rw", uri=True, timeout=0)
        try:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("COMMIT")
            ocupado = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
            modo = None if ocupado else conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.OperationalError as erro:
        raise RestauracaoRecusada(FECHE_OS_PROGRAMAS) from erro
    restos = [p for p in (Path(f"{db}-wal"), Path(f"{db}-shm")) if p.exists()]
    if modo != "delete" or restos:
        raise RestauracaoRecusada(FECHE_OS_PROGRAMAS)


def _voltar_wal(db: Path) -> None:
    """Melhor esforço: a aplicação também liga o WAL em toda conexão."""
    try:
        conn = sqlite3.connect(f"{db.resolve().as_uri()}?mode=rw", uri=True, timeout=0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _ids(conn: sqlite3.Connection, anonimizados: bool) -> set[int]:
    condicao = "IS NOT NULL" if anonimizados else "IS NULL"
    try:
        sql = f"SELECT id FROM clientes WHERE anonimizado_em {condicao}"  # noqa: S608 (fixo)
        return {r[0] for r in conn.execute(sql)}
    finally:
        conn.close()


def _checar_anonimizacao(db: Path, staging: Path, aceitar: bool) -> None:
    """Recusa só quem está anonimizado agora e volta com dados no backup.

    Cliente criado depois do backup não existe nele, e quem já estava anonimizado no backup
    não traz nada de volta: nenhum dos dois é reintrodução.
    """
    try:
        atual = sqlite3.connect(f"{db.resolve().as_uri()}?mode=rw", uri=True, timeout=0)
        anonimizados_agora = _ids(atual, anonimizados=True)
    except sqlite3.OperationalError as erro:  # outro programa segura o banco
        raise RestauracaoRecusada(FECHE_OS_PROGRAMAS) from erro
    reintroduzidos = anonimizados_agora & _ids(abrir_leitura(staging), anonimizados=False)
    if reintroduzidos and not aceitar:
        raise RestauracaoRecusada(
            f"O backup é anterior à anonimização de {len(reintroduzidos)} cliente(s) e traria "
            "os dados de volta. Se for isso mesmo, repita com --aceitar-reintroducao."
        )


def _recuperar(db: Path, controle: Path) -> str:
    """Leva qualquer estado inacabado a um fim seguro, olhando os arquivos reais."""
    dados: dict[str, Any] = json.loads(controle.read_text(encoding="utf-8"))
    estado = str(dados["estado"])
    staging, pre = Path(dados["staging"]), Path(dados["pre_restore"])
    if estado in ("verified", "done"):
        _arquivar(controle, dados, "done")
        return estado
    if pre.exists():
        if db.exists():  # o banco novo chegou a entrar: é guardado, nunca apagado
            _mover(db, db.with_name(f"{db.name}.failed-{dados['carimbo']}"))
        _mover(pre, db)
    if not db.exists():
        raise RuntimeError(
            f"Banco ausente e sem cópia `.pre-restore`. Use o backup de segurança: "
            f"{dados.get('seguranca')}"
        )
    staging.unlink(missing_ok=True)  # cópia temporária do backup, que continua intacto
    _voltar_wal(db)
    _arquivar(controle, dados, "aborted")
    return estado


def restaurar(
    db: Path, arquivo: Path, pasta_backups: Path, aceitar_reintroducao: bool = False
) -> Path:
    """Troca o banco pelo backup e devolve o caminho do original preservado."""
    with trava(caminho_trava(db)):
        if controle_pendente(db):
            raise RestauracaoRecusada(
                "Há uma restauração inacabada. Rode `uv run salesos recover` primeiro."
            )
        if not db.exists():
            raise RestauracaoRecusada(f"Banco atual não encontrado: {db}")
        marca = carimbo()
        staging = db.with_name(f"{db.name}.staging-{marca}")
        pre = db.with_name(f"{db.name}.pre-restore-{marca}")
        dados: dict[str, Any] = {
            "carimbo": marca,
            "banco": str(db),
            "backup": str(arquivo),
            "staging": str(staging),
            "pre_restore": str(pre),
            "seguranca": None,
        }
        controle = caminho_controle(db)
        try:
            _gravar_estado(controle, dados, "validating")
            _copiar(arquivo, staging)
            try:
                verificar_backup(staging, manifesto_de=arquivo)
            except BackupInvalido as erro:
                raise RestauracaoRecusada(f"Backup recusado: {erro}. Nada foi alterado.") from erro
            _checar_anonimizacao(db, staging, aceitar_reintroducao)
            _aquietar(db)
            _gravar_estado(controle, dados, "quiesced")
            seguranca = criar_backup(db, pasta_backups, prefixo="pre-restore")
            verificar_backup(seguranca, exigir_revisao=False)
            dados["seguranca"] = str(seguranca)
            _gravar_estado(controle, dados, "safety_backed_up")
            _mover(db, pre)
            _gravar_estado(controle, dados, "original_moved")
            _mover(staging, db)
            _gravar_estado(controle, dados, "swapped")
            verificar_backup(db, manifesto_de=arquivo)
            _voltar_wal(db)
            _gravar_estado(controle, dados, "verified")
        except Exception:
            try:
                _recuperar(db, controle)
            except Exception:
                # O diário continua pendente; o erro original segue para quem chamou.
                logger.warning("Não foi possível desfazer agora; rode `salesos recover`.")
            raise
        _arquivar(controle, dados, "done")
        return pre


def recuperar(db: Path, pasta_backups: Path | None = None) -> Recuperacao:
    """Termina uma restauração interrompida e relata sobras temporárias (sem apagá-las)."""
    with trava(caminho_trava(db)):
        controle = controle_pendente(db)
        estado = _recuperar(db, controle) if controle else None
        residuos = sorted(db.parent.glob(f"{db.name}.staging-*"))
        if pasta_backups is not None and pasta_backups.exists():
            residuos += sorted(pasta_backups.glob("*.tmp"))
        return Recuperacao(estado, residuos)
