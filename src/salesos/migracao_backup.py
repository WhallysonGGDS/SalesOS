"""B1: backup de revisão anterior vira um backup verificado na revisão atual (ADR 0005).

O original só é lido. A migração roda numa cópia em `<pasta de backups>/.migracao-<carimbo>/`,
apagada ao final; o resultado é um backup comum (`migrado-<carimbo>.db` + manifesto), que o
`restaurar` de sempre recebe com todas as suas proteções. O banco atual não é tocado aqui.
"""

import logging
import os
import shutil
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from salesos.backup import (
    MIGRATIONS,
    BackupInvalido,
    caminho_manifesto,
    carimbo,
    criar_backup,
    publicar,
    revisao_atual,
    sha256_arquivo,
    verificar_backup,
    verificar_integridade,
)
from salesos.db import restringir
from salesos.restore import RestauracaoRecusada

logger = logging.getLogger(__name__)

PREFIXO_TEMPORARIO = ".migracao-"


def revisoes_anteriores() -> tuple[str, ...]:
    """Revisões da cadeia, da base até a anterior ao head (as únicas aceitas para migrar)."""
    cadeia = [s.revision for s in ScriptDirectory(str(MIGRATIONS)).walk_revisions()]
    return tuple(reversed(cadeia[1:]))  # walk_revisions vai do head para a base


def _recusa(motivo: str) -> RestauracaoRecusada:
    return RestauracaoRecusada(f"Backup não migrado: {motivo}. Nada foi alterado.")


def _upgrade(copia: Path) -> None:
    config = Config()  # sem arquivo: o env.py não reconfigura os logs
    config.set_main_option("script_location", str(MIGRATIONS))
    # O ConfigParser interpreta `%`: uma pasta como "100%" quebraria a URL.
    config.set_main_option("sqlalchemy.url", f"sqlite:///{copia}".replace("%", "%%"))
    command.upgrade(config, "head")


def migrar_backup(arquivo: Path, pasta_backups: Path) -> Path:
    """Devolve um backup verificado na revisão atual; o próprio arquivo se já estiver nela."""
    try:
        manifesto = verificar_backup(arquivo, exigir_revisao=False)
        revisao = verificar_integridade(arquivo)
    except BackupInvalido as erro:
        raise _recusa(str(erro)) from erro
    if revisao == revisao_atual():
        return arquivo
    if revisao not in revisoes_anteriores():
        raise _recusa(f"revisão {revisao} desconhecida ou mais nova que a atual")

    pasta_backups.mkdir(parents=True, exist_ok=True)
    restringir(pasta_backups, 0o700)
    temporaria = pasta_backups / f"{PREFIXO_TEMPORARIO}{carimbo()}"
    temporaria.mkdir()
    restringir(temporaria, 0o700)
    try:
        copia = temporaria / "salesos.db"
        shutil.copyfile(arquivo, copia)
        restringir(copia)
        if sha256_arquivo(copia) != manifesto.get("sha256"):  # mudou depois da verificação
            raise _recusa("SHA-256 do arquivo diverge do manifesto")
        _upgrade(copia)
        # Gerado e verificado dentro da pasta temporária: um migrado não verificado nunca
        # aparece entre os backups, nem se o processo for interrompido.
        novo = criar_backup(copia, temporaria / "saida", prefixo="migrado")
        verificar_backup(novo)  # revisão atual e estrutura esperada
        final = pasta_backups / novo.name
        publicar(novo, final)  # nunca sobrescreve
        try:
            publicar(caminho_manifesto(novo), caminho_manifesto(final))
        except BaseException:
            final.unlink(missing_ok=True)  # sem manifesto seria um backup inútil; é nosso
            raise
        return final
    except RestauracaoRecusada:
        raise
    except Exception as erro:
        # Só textos nossos (BackupInvalido, falha de FK); erros do SQLite viram o nome do tipo.
        motivo = (
            str(erro) if isinstance(erro, BackupInvalido | RuntimeError) else type(erro).__name__
        )
        raise _recusa(f"a migração falhou ({motivo})") from erro
    finally:
        shutil.rmtree(temporaria, ignore_errors=True)
        if os.path.lexists(temporaria):  # no Windows, um arquivo aberto impede apagar
            logger.warning(
                "Pasta temporária da migração não foi apagada: %s (contém dados; apague-a)",
                temporaria.name,
            )
