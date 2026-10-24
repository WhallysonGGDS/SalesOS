"""Modelo de dados da Fase 02 (clientes, contatos e interações).

Telefone fica fora do banco até as regras da Anatel serem aprovadas (D12). A coluna
`documento` existe, mas não é preenchida pela aplicação até CPF e CNPJ terem fonte
oficial (D6, D11).
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from salesos.db import Base

TIPOS_CLIENTE = ("PF", "PJ")
ORIGENS = (
    "indicacao",
    "site",
    "instagram",
    "linkedin",
    "whatsapp",
    "evento",
    "prospeccao_ativa",
    "outro",
)
TIPOS_INTERACAO = ("ligacao", "reuniao", "mensagem", "email", "nota", "sistema")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (
        CheckConstraint(_in("tipo", TIPOS_CLIENTE), name="tipo"),
        CheckConstraint(_in("origem", ORIGENS), name="origem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(2))
    nome: Mapped[str] = mapped_column(String(200), index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(200))
    documento: Mapped[str | None] = mapped_column(String(14), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    origem: Mapped[str] = mapped_column(String(20))
    observacoes: Mapped[str | None] = mapped_column(Text)
    # Texto normalizado para busca (search_key); recalculado pelo serviço a cada escrita.
    busca: Mapped[str] = mapped_column(Text, server_default="")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anonimizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Contato(Base):
    __tablename__ = "contatos"
    __table_args__ = (UniqueConstraint("cliente_id", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    nome: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Interacao(Base):
    """Histórico só de acréscimo (D5): não há edição nem exclusão comum."""

    __tablename__ = "interacoes"
    __table_args__ = (
        CheckConstraint(_in("tipo", TIPOS_INTERACAO), name="tipo"),
        Index("ix_interacoes_cliente_id_ocorrida_em", "cliente_id", "ocorrida_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"))
    contato_id: Mapped[int | None] = mapped_column(
        ForeignKey("contatos.id", ondelete="SET NULL"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(10))
    ocorrida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resumo: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
