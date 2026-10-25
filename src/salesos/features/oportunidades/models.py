"""Modelo de dados da Fase 03 (oportunidades e funil, ADR 0006).

`movimentacoes` é só de acréscimo: nenhuma função nem rota edita ou apaga uma linha.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from salesos.db import Base
from salesos.dinheiro import MAXIMO_CENTAVOS

ETAPAS_ABERTAS = ("novo_lead", "qualificacao", "proposta_enviada", "negociacao")
ETAPAS_FINAIS = ("ganha", "perdida")
ETAPAS = ETAPAS_ABERTAS + ETAPAS_FINAIS
MOTIVOS_PERDA = ("preco", "concorrente", "sem_orcamento", "sem_resposta", "adiado", "outro")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Oportunidade(Base):
    __tablename__ = "oportunidades"
    __table_args__ = (
        CheckConstraint(_in("etapa", ETAPAS), name="etapa"),
        CheckConstraint(
            "(etapa = 'perdida') = (motivo_perda IS NOT NULL)", name="perdida_com_motivo"
        ),
        CheckConstraint(
            f"motivo_perda IS NULL OR {_in('motivo_perda', MOTIVOS_PERDA)}", name="motivo_perda"
        ),
        CheckConstraint(
            f"({_in('etapa', ETAPAS_FINAIS)}) = (fechada_em IS NOT NULL)", name="fechada_em"
        ),
        CheckConstraint(
            "valor_centavos IS NULL OR (typeof(valor_centavos) = 'integer' "
            f"AND valor_centavos BETWEEN 0 AND {MAXIMO_CENTAVOS})",
            name="valor_centavos",
        ),
        # Explícito: no SQLite, NULL > 0 resulta em NULL e o CHECK passaria.
        CheckConstraint(
            "etapa <> 'ganha' OR (valor_centavos IS NOT NULL AND valor_centavos > 0)",
            name="ganha_com_valor",
        ),
        Index("ix_oportunidades_etapa_created_at", "etapa", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    titulo: Mapped[str] = mapped_column(String(200))
    etapa: Mapped[str] = mapped_column(String(20))
    valor_centavos: Mapped[int | None] = mapped_column(BigInteger)
    previsao_fechamento: Mapped[date | None] = mapped_column(Date)
    fechada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    motivo_perda: Mapped[str | None] = mapped_column(String(20))
    motivo_detalhe: Mapped[str | None] = mapped_column(String(500))
    observacoes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Movimentacao(Base):
    """Histórico das mudanças de etapa. `de_etapa` é nula só na criação."""

    __tablename__ = "movimentacoes"
    __table_args__ = (
        CheckConstraint(
            f"de_etapa IS NULL OR ({_in('de_etapa', ETAPAS)} AND de_etapa <> para_etapa)",
            name="de_etapa",
        ),
        CheckConstraint(_in("para_etapa", ETAPAS), name="para_etapa"),
        Index("ix_movimentacoes_oportunidade_id_ocorrida_em", "oportunidade_id", "ocorrida_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    oportunidade_id: Mapped[int] = mapped_column(
        ForeignKey("oportunidades.id", ondelete="RESTRICT")
    )
    de_etapa: Mapped[str | None] = mapped_column(String(20))
    para_etapa: Mapped[str] = mapped_column(String(20))
    ocorrida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
