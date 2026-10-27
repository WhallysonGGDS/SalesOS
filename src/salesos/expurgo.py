"""Expurgo manual de clientes anonimizados há 12 meses ou mais (P1, `docs/privacy.md`).

Só roda pelo comando `salesos expurgar`, com confirmação; nada o chama automaticamente.
Apaga o cliente e tudo o que depende dele numa única transação, das folhas para a raiz
(todas as chaves estrangeiras são RESTRICT). Não guarda agregados.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select, text
from sqlalchemy.orm import Session

from salesos.features.clientes.models import Cliente, Contato, Interacao
from salesos.features.oportunidades.models import Movimentacao, Oportunidade
from salesos.features.tarefas.models import Tarefa, TarefaEvento

logger = logging.getLogger(__name__)

PRAZO_ANOS = 1  # 12 meses do calendário (política P1)
EXPURGO_MAX = 200  # por execução; o resto aparece na próxima
ROTULOS = {
    "tarefa_eventos": "registro(s) do histórico das tarefas",
    "tarefas": "tarefa(s)",
    "movimentacoes": "registro(s) do histórico de etapas",
    "oportunidades": "oportunidade(s)",
    "interacoes": "interação(ões) e evento(s) da linha do tempo",
    "contatos": "contato(s)",
    "clientes": "cliente(s)",
}


def descrever(linhas: dict[str, int]) -> str:
    """Contagens em português, sem nomes de tabela e sem dados das pessoas."""
    return ", ".join(f"{n} {ROTULOS[t]}" for t, n in linhas.items() if n) or "nada"


class ExpurgoRecusado(RuntimeError):
    pass


@dataclass(frozen=True)
class Abrangencia:
    cliente_id: int
    anonimizado_em: datetime
    linhas: dict[str, int]


def limite(agora: datetime) -> datetime:
    """Anonimizados até este momento (UTC, sem fuso, como gravado) entram no expurgo."""
    utc = agora.astimezone(UTC).replace(tzinfo=None)
    try:
        return utc.replace(year=utc.year - PRAZO_ANOS)
    except ValueError:  # 29 de fevereiro: o ano anterior não tem esse dia
        return utc.replace(year=utc.year - PRAZO_ANOS, day=28)


def _alvos(ids: Sequence[int]) -> list[tuple[Any, ColumnElement[bool]]]:
    """Tabelas na ordem de exclusão e a condição de cada uma (uma fonte para contar e apagar)."""
    tarefas = select(Tarefa.id).where(Tarefa.cliente_id.in_(ids))
    oportunidades = select(Oportunidade.id).where(Oportunidade.cliente_id.in_(ids))
    return [
        (TarefaEvento, TarefaEvento.tarefa_id.in_(tarefas)),
        (Tarefa, Tarefa.cliente_id.in_(ids)),
        (Movimentacao, Movimentacao.oportunidade_id.in_(oportunidades)),
        (Oportunidade, Oportunidade.cliente_id.in_(ids)),
        (Interacao, Interacao.cliente_id.in_(ids)),
        (Contato, Contato.cliente_id.in_(ids)),
        (Cliente, Cliente.id.in_(ids)),
    ]


def _elegiveis(agora: datetime) -> ColumnElement[bool]:
    return Cliente.anonimizado_em.is_not(None) & (Cliente.anonimizado_em <= limite(agora))


def abrangencia(session: Session, agora: datetime | None = None) -> list[Abrangencia]:
    """Clientes que podem ser expurgados agora e quantas linhas sairiam de cada tabela."""
    agora = agora or datetime.now(UTC)
    query = (
        select(Cliente.id, Cliente.anonimizado_em)
        .where(_elegiveis(agora))
        .order_by(Cliente.id)
        .limit(EXPURGO_MAX)
    )
    escopo = []
    for cliente_id, anonimizado_em in session.execute(query):
        if anonimizado_em is None:  # a consulta já exclui; só para o tipo
            continue
        linhas = {
            tabela.__tablename__: session.scalar(select(func.count()).where(condicao)) or 0
            for tabela, condicao in _alvos([cliente_id])
        }
        escopo.append(Abrangencia(cliente_id, anonimizado_em, linhas))
    return escopo


def _conferir(session: Session, ids: Sequence[int], agora: datetime) -> None:
    elegiveis = set(
        session.scalars(select(Cliente.id).where(Cliente.id.in_(ids), _elegiveis(agora)))
    )
    if not ids or elegiveis != set(ids):
        raise ExpurgoRecusado("cliente fora do escopo do expurgo; nada foi apagado")
    # D1 proíbe, mas o banco não impede: apagar exigiria mexer no registro de outro cliente.
    oportunidades = select(Oportunidade.id).where(Oportunidade.cliente_id.in_(ids))
    contatos = select(Contato.id).where(Contato.cliente_id.in_(ids))
    alheios = session.scalar(
        select(func.count()).where(
            Tarefa.oportunidade_id.in_(oportunidades) & Tarefa.cliente_id.not_in(ids)
        )
    ) or session.scalar(
        select(func.count()).where(
            Interacao.contato_id.in_(contatos) & Interacao.cliente_id.not_in(ids)
        )
    )
    if alheios:
        raise ExpurgoRecusado(
            "registro de outro cliente aponta para um expurgado; nada foi apagado"
        )


def expurgar(session: Session, ids: Sequence[int], agora: datetime | None = None) -> dict[str, int]:
    """Apaga os clientes e tudo o que é deles, num único commit; devolve linhas por tabela."""
    agora = agora or datetime.now(UTC)
    _conferir(session, ids, agora)
    relatorio = {}
    for tabela, condicao in _alvos(ids):
        resultado = session.execute(delete(tabela).where(condicao))
        relatorio[tabela.__tablename__] = int(getattr(resultado, "rowcount", 0) or 0)
    session.commit()
    # Como na anonimização: `secure_delete` zera o conteúdo; o checkpoint esvazia o `-wal`.
    ocupado, paginas, copiadas = session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).one()
    session.commit()
    if ocupado or copiadas < paginas:
        # Outro programa lendo o banco: o conteúdo apagado pode ficar até o próximo checkpoint.
        logger.warning(
            "Checkpoint do WAL incompleto após o expurgo: os dados apagados podem continuar no "
            "arquivo -wal até o próximo checkpoint. Feche outros programas que usem o banco."
        )
    return relatorio
