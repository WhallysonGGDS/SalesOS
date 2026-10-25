"""Fase 03: oportunidades e funil (ADR 0006).

`movimentacoes` é só de acréscimo. CHECKs garantem no banco: motivo só e sempre na perda,
fechamento só e sempre nas etapas finais, ganha com valor positivo (NULL explícito, porque
no SQLite NULL > 0 deixaria passar) e valor inteiro entre 0 e 10**12 centavos
(`typeof`, porque o SQLite aceitaria 0.5 numa coluna INTEGER).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25 02:05:11.286645

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria as tabelas da Fase 03."""
    op.create_table(
        "oportunidades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("etapa", sa.String(length=20), nullable=False),
        sa.Column("valor_centavos", sa.BigInteger(), nullable=True),
        sa.Column("previsao_fechamento", sa.Date(), nullable=True),
        sa.Column("fechada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_perda", sa.String(length=20), nullable=True),
        sa.Column("motivo_detalhe", sa.String(length=500), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(etapa = 'perdida') = (motivo_perda IS NOT NULL)",
            name=op.f("ck_oportunidades_perdida_com_motivo"),
        ),
        sa.CheckConstraint(
            "(etapa IN ('ganha', 'perdida')) = (fechada_em IS NOT NULL)",
            name=op.f("ck_oportunidades_fechada_em"),
        ),
        sa.CheckConstraint(
            "etapa <> 'ganha' OR (valor_centavos IS NOT NULL AND valor_centavos > 0)",
            name=op.f("ck_oportunidades_ganha_com_valor"),
        ),
        sa.CheckConstraint(
            "etapa IN ('novo_lead', 'qualificacao', 'proposta_enviada', 'negociacao', "
            "'ganha', 'perdida')",
            name=op.f("ck_oportunidades_etapa"),
        ),
        sa.CheckConstraint(
            "motivo_perda IS NULL OR motivo_perda IN ('preco', 'concorrente', 'sem_orcamento', "
            "'sem_resposta', 'adiado', 'outro')",
            name=op.f("ck_oportunidades_motivo_perda"),
        ),
        sa.CheckConstraint(
            "valor_centavos IS NULL OR (typeof(valor_centavos) = 'integer' "
            "AND valor_centavos BETWEEN 0 AND 1000000000000)",
            name=op.f("ck_oportunidades_valor_centavos"),
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name=op.f("fk_oportunidades_cliente_id_clientes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oportunidades")),
    )
    with op.batch_alter_table("oportunidades", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_oportunidades_cliente_id"), ["cliente_id"], unique=False
        )
        batch_op.create_index(
            "ix_oportunidades_etapa_created_at", ["etapa", "created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_oportunidades_fechada_em"), ["fechada_em"], unique=False
        )

    op.create_table(
        "movimentacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oportunidade_id", sa.Integer(), nullable=False),
        sa.Column("de_etapa", sa.String(length=20), nullable=True),
        sa.Column("para_etapa", sa.String(length=20), nullable=False),
        sa.Column("ocorrida_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "de_etapa IS NULL OR (de_etapa IN ('novo_lead', 'qualificacao', 'proposta_enviada', "
            "'negociacao', 'ganha', 'perdida') AND de_etapa <> para_etapa)",
            name=op.f("ck_movimentacoes_de_etapa"),
        ),
        sa.CheckConstraint(
            "para_etapa IN ('novo_lead', 'qualificacao', 'proposta_enviada', 'negociacao', "
            "'ganha', 'perdida')",
            name=op.f("ck_movimentacoes_para_etapa"),
        ),
        sa.ForeignKeyConstraint(
            ["oportunidade_id"],
            ["oportunidades.id"],
            name=op.f("fk_movimentacoes_oportunidade_id_oportunidades"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimentacoes")),
    )
    with op.batch_alter_table("movimentacoes", schema=None) as batch_op:
        batch_op.create_index(
            "ix_movimentacoes_oportunidade_id_ocorrida_em",
            ["oportunidade_id", "ocorrida_em"],
            unique=False,
        )


def downgrade() -> None:
    """Remove só as tabelas da Fase 03; clientes, contatos e interações ficam."""
    with op.batch_alter_table("movimentacoes", schema=None) as batch_op:
        batch_op.drop_index("ix_movimentacoes_oportunidade_id_ocorrida_em")

    op.drop_table("movimentacoes")
    with op.batch_alter_table("oportunidades", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_oportunidades_fechada_em"))
        batch_op.drop_index("ix_oportunidades_etapa_created_at")
        batch_op.drop_index(batch_op.f("ix_oportunidades_cliente_id"))

    op.drop_table("oportunidades")
