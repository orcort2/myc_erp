"""add repair warranty cycles

Revision ID: 62f12534fc33
Revises: 70d92d9b36bf
Create Date: 2026-08-20 16:08:49.400788
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '62f12534fc33'
down_revision: Union[str, None] = '70d92d9b36bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ciclos de garantía versionados sobre RepairExecution. Ver
    # app/models/repair_execution.py:RepairWarrantyCycle.
    op.create_table(
        'repair_warranty_cycles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repair_execution_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('opened_by_id', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution', sa.String(length=30), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repair_execution_id', 'sequence', name='uq_repair_warranty_cycle_sequence'),
        sa.CheckConstraint('sequence > 0', name='ck_repair_warranty_cycle_sequence_positive'),
        sa.CheckConstraint("status IN ('open','closed')", name='ck_repair_warranty_cycle_status'),
        sa.CheckConstraint(
            "resolution IS NULL OR resolution IN ('repaired','equipment_not_suitable')",
            name='ck_repair_warranty_cycle_resolution',
        ),
        sa.ForeignKeyConstraint(
            ['repair_execution_id'], ['repair_executions.id'],
            name='fk_repair_warranty_cycles_execution',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['opened_by_id'], ['users.id'],
            name='fk_repair_warranty_cycles_opened_by',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['closed_by_id'], ['users.id'],
            name='fk_repair_warranty_cycles_closed_by',
            ondelete='RESTRICT',
        ),
    )

    op.create_index('ix_repair_warranty_cycles_repair_execution_id', 'repair_warranty_cycles', ['repair_execution_id'])
    op.create_index('ix_repair_warranty_cycles_sequence', 'repair_warranty_cycles', ['sequence'])
    op.create_index('ix_repair_warranty_cycles_status', 'repair_warranty_cycles', ['status'])
    op.create_index('ix_repair_warranty_cycles_opened_by_id', 'repair_warranty_cycles', ['opened_by_id'])
    op.create_index('ix_repair_warranty_cycles_closed_by_id', 'repair_warranty_cycles', ['closed_by_id'])

    # Fotografía inmutable del cierre del ciclo original (ver Decisión #12
    # en app/models/repair_execution.py). Nullable y sin backfill retroactivo:
    # ejecuciones ya cerradas antes de esta migración simplemente no tendrán
    # esta fotografía hasta que su historial deje de ser relevante.
    op.add_column('repair_executions', sa.Column('original_conclusion', sa.String(length=30), nullable=True))
    op.add_column('repair_executions', sa.Column('original_conclusion_reason', sa.Text(), nullable=True))
    op.add_column('repair_executions', sa.Column('original_technical_completed_at', sa.DateTime(timezone=True), nullable=True))

    # warranty_cycle_id nullable en el trabajo técnico existente: NULL sigue
    # significando "ciclo original", sin migrar retrospectivamente filas
    # existentes hacia ciclos artificiales.
    for table in ('repair_interventions', 'repair_tests', 'repair_pauses', 'repair_change_requests'):
        op.add_column(table, sa.Column('warranty_cycle_id', sa.Integer(), nullable=True))
        op.create_index(f'ix_{table}_warranty_cycle_id', table, ['warranty_cycle_id'])
        op.create_foreign_key(
            f'fk_{table}_warranty_cycle',
            table,
            'repair_warranty_cycles',
            ['warranty_cycle_id'],
            ['id'],
            ondelete='RESTRICT',
        )


def downgrade() -> None:
    for table in ('repair_interventions', 'repair_tests', 'repair_pauses', 'repair_change_requests'):
        op.drop_constraint(f'fk_{table}_warranty_cycle', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_warranty_cycle_id', table_name=table)
        op.drop_column(table, 'warranty_cycle_id')

    op.drop_column('repair_executions', 'original_technical_completed_at')
    op.drop_column('repair_executions', 'original_conclusion_reason')
    op.drop_column('repair_executions', 'original_conclusion')

    op.drop_index('ix_repair_warranty_cycles_closed_by_id', table_name='repair_warranty_cycles')
    op.drop_index('ix_repair_warranty_cycles_opened_by_id', table_name='repair_warranty_cycles')
    op.drop_index('ix_repair_warranty_cycles_status', table_name='repair_warranty_cycles')
    op.drop_index('ix_repair_warranty_cycles_sequence', table_name='repair_warranty_cycles')
    op.drop_index('ix_repair_warranty_cycles_repair_execution_id', table_name='repair_warranty_cycles')
    op.drop_table('repair_warranty_cycles')
