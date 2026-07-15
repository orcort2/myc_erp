"""invoice_workbench_review

Revision ID: 640da69de732
Revises: fc3d4e5f6a7
Create Date: 2026-07-14 13:07:16.820992
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '640da69de732'
down_revision: Union[str, None] = 'fc3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoices',
        sa.Column(
            'review_required',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        'invoices',
        sa.Column(
            'draft_reason',
            sa.String(length=80),
            nullable=True,
        ),
    )

    op.add_column(
        'invoices',
        sa.Column(
            'source_snapshot',
            sa.JSON(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f('ix_invoices_review_required'),
        'invoices',
        ['review_required'],
        unique=False,
    )

    op.create_index(
        op.f('ix_invoices_draft_reason'),
        'invoices',
        ['draft_reason'],
        unique=False,
    )

    op.alter_column(
        'invoices',
        'review_required',
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_invoices_draft_reason'),
        table_name='invoices',
    )

    op.drop_index(
        op.f('ix_invoices_review_required'),
        table_name='invoices',
    )

    op.drop_column('invoices', 'source_snapshot')
    op.drop_column('invoices', 'draft_reason')
    op.drop_column('invoices', 'review_required')
