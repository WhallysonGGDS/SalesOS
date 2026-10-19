"""Linha de base da Fase 01: nenhuma tabela de negócio ainda.

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """As tabelas do CRM chegam a partir da Fase 02."""


def downgrade() -> None:
    """Nada a desfazer além do registro de versão, que o Alembic remove."""
