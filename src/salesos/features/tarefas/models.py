"""Modelo de dados da Fase 04 (tarefas e follow-ups, ADR 0007).

`tarefa_eventos` é só de acréscimo: nenhuma função nem rota edita ou apaga uma linha.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from salesos.db import Base

TIPOS_TAREFA = ("ligacao", "reuniao", "mensagem", "retorno")
PRIORIDADES = ("baixa", "normal", "alta")
ESTADOS = ("pendente", "concluida", "cancelada")
ACOES = ("criada", "concluida", "cancelada", "reaberta")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Tarefa(Base):
    __tablename__ = "tarefas"
    __table_args__ = (
        CheckConstraint(_in("tipo", TIPOS_TAREFA), name="tipo"),
        CheckConstraint(_in("prioridade", PRIORIDADES), name="prioridade"),
        CheckConstraint(_in("estado", ESTADOS), name="estado"),
        CheckConstraint("(estado = 'concluida') = (concluida_em IS NOT NULL)", name="concluida"),
        CheckConstraint("(estado = 'cancelada') = (cancelada_em IS NOT NULL)", name="cancelada"),
        Index("ix_tarefas_estado_prazo", "estado", "prazo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    # Do mesmo cliente: garantido pelo serviço (um CHECK do SQLite não consulta outra tabela).
    oportunidade_id: Mapped[int | None] = mapped_column(
        ForeignKey("oportunidades.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    prioridade: Mapped[str] = mapped_column(String(10), server_default="normal")
    prazo: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(10), server_default="pendente")
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TarefaEvento(Base):
    """Histórico de conclusão (D6): criação, conclusão, cancelamento e reabertura."""

    __tablename__ = "tarefa_eventos"
    __table_args__ = (
        CheckConstraint(_in("acao", ACOES), name="acao"),
        Index("ix_tarefa_eventos_tarefa_id_ocorrida_em", "tarefa_id", "ocorrida_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tarefa_id: Mapped[int] = mapped_column(ForeignKey("tarefas.id", ondelete="RESTRICT"))
    acao: Mapped[str] = mapped_column(String(10))
    ocorrida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
