"""Fase 02: clientes, contatos e interações.

Telefone fica fora até as regras da Anatel serem aprovadas (D12); `documento` existe, mas só
será preenchido quando CPF e CNPJ tiverem fonte oficial (D6, D11).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24 19:48:54.678054

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria as tabelas da Fase 02."""
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=2), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("nome_fantasia", sa.String(length=200), nullable=True),
        sa.Column("documento", sa.String(length=14), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("busca", sa.Text(), server_default="", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonimizado_em", sa.DateTime(timezone=True), nullable=True),
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
            "origem IN ('indicacao', 'site', 'instagram', 'linkedin', 'whatsapp', 'evento', "
            "'prospeccao_ativa', 'outro')",
            name=op.f("ck_clientes_origem"),
        ),
        sa.CheckConstraint("tipo IN ('PF', 'PJ')", name=op.f("ck_clientes_tipo")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clientes")),
        sa.UniqueConstraint("documento", name=op.f("uq_clientes_documento")),
        sa.UniqueConstraint("email", name=op.f("uq_clientes_email")),
    )
    with op.batch_alter_table("clientes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_clientes_nome"), ["nome"], unique=False)

    op.create_table(
        "contatos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("cargo", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name=op.f("fk_contatos_cliente_id_clientes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contatos")),
        sa.UniqueConstraint("cliente_id", "email", name=op.f("uq_contatos_cliente_id_email")),
    )
    with op.batch_alter_table("contatos", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_contatos_cliente_id"), ["cliente_id"], unique=False)

    op.create_table(
        "interacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("contato_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("ocorrida_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resumo", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('ligacao', 'reuniao', 'mensagem', 'email', 'nota', 'sistema')",
            name=op.f("ck_interacoes_tipo"),
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name=op.f("fk_interacoes_cliente_id_clientes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contato_id"],
            ["contatos.id"],
            name=op.f("fk_interacoes_contato_id_contatos"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interacoes")),
    )
    with op.batch_alter_table("interacoes", schema=None) as batch_op:
        batch_op.create_index(
            "ix_interacoes_cliente_id_ocorrida_em", ["cliente_id", "ocorrida_em"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_interacoes_contato_id"), ["contato_id"], unique=False)


def downgrade() -> None:
    """Remove as tabelas da Fase 02 (só para reversão em banco de teste)."""
    with op.batch_alter_table("interacoes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_interacoes_contato_id"))
        batch_op.drop_index("ix_interacoes_cliente_id_ocorrida_em")

    op.drop_table("interacoes")
    with op.batch_alter_table("contatos", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_contatos_cliente_id"))

    op.drop_table("contatos")
    with op.batch_alter_table("clientes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_clientes_nome"))

    op.drop_table("clientes")
