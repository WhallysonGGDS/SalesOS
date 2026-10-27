"""Fase 04: tarefas e follow-ups (ADR 0007).

`tarefa_eventos` é só de acréscimo. CHECKs garantem no banco: tipo, prioridade, estado e ação
da lista; `concluida_em` só e sempre em `concluida`; `cancelada_em` só e sempre em `cancelada`.
Que a oportunidade seja do mesmo cliente é regra do serviço.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 01:48:29.649106

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria as tabelas da Fase 04."""
    op.create_table(
        "tarefas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("oportunidade_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("prioridade", sa.String(length=10), server_default="normal", nullable=False),
        sa.Column("prazo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=10), server_default="pendente", nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelada_em", sa.DateTime(timezone=True), nullable=True),
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
            "(estado = 'cancelada') = (cancelada_em IS NOT NULL)", name=op.f("ck_tarefas_cancelada")
        ),
        sa.CheckConstraint(
            "(estado = 'concluida') = (concluida_em IS NOT NULL)", name=op.f("ck_tarefas_concluida")
        ),
        sa.CheckConstraint(
            "estado IN ('pendente', 'concluida', 'cancelada')", name=op.f("ck_tarefas_estado")
        ),
        sa.CheckConstraint(
            "prioridade IN ('baixa', 'normal', 'alta')", name=op.f("ck_tarefas_prioridade")
        ),
        sa.CheckConstraint(
            "tipo IN ('ligacao', 'reuniao', 'mensagem', 'retorno')", name=op.f("ck_tarefas_tipo")
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name=op.f("fk_tarefas_cliente_id_clientes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["oportunidade_id"],
            ["oportunidades.id"],
            name=op.f("fk_tarefas_oportunidade_id_oportunidades"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tarefas")),
    )
    with op.batch_alter_table("tarefas", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tarefas_cliente_id"), ["cliente_id"], unique=False)
        batch_op.create_index("ix_tarefas_estado_prazo", ["estado", "prazo"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_tarefas_oportunidade_id"), ["oportunidade_id"], unique=False
        )

    op.create_table(
        "tarefa_eventos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tarefa_id", sa.Integer(), nullable=False),
        sa.Column("acao", sa.String(length=10), nullable=False),
        sa.Column("ocorrida_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "acao IN ('criada', 'concluida', 'cancelada', 'reaberta')",
            name=op.f("ck_tarefa_eventos_acao"),
        ),
        sa.ForeignKeyConstraint(
            ["tarefa_id"],
            ["tarefas.id"],
            name=op.f("fk_tarefa_eventos_tarefa_id_tarefas"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tarefa_eventos")),
    )
    with op.batch_alter_table("tarefa_eventos", schema=None) as batch_op:
        batch_op.create_index(
            "ix_tarefa_eventos_tarefa_id_ocorrida_em", ["tarefa_id", "ocorrida_em"], unique=False
        )


def downgrade() -> None:
    """Remove só as tabelas da Fase 04; o resto fica."""
    with op.batch_alter_table("tarefa_eventos", schema=None) as batch_op:
        batch_op.drop_index("ix_tarefa_eventos_tarefa_id_ocorrida_em")

    op.drop_table("tarefa_eventos")
    with op.batch_alter_table("tarefas", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tarefas_oportunidade_id"))
        batch_op.drop_index("ix_tarefas_estado_prazo")
        batch_op.drop_index(batch_op.f("ix_tarefas_cliente_id"))

    op.drop_table("tarefas")
