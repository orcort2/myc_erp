"""Add append-only Certificate resolution operations.

Revision ID: f9c1d3e5a7b9
Revises: f8a0b2c4d6e8
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f9c1d3e5a7b9"
down_revision: str | None = "f8a0b2c4d6e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_document = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )
    op.create_table(
        "certificate_resolution_operations",
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("source_operation_id", sa.Integer(), nullable=True),
        sa.Column("operation_key", sa.String(length=200), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column("request_payload", json_document, nullable=False),
        sa.Column("before_snapshot", json_document, nullable=False),
        sa.Column("after_snapshot", json_document, nullable=False),
        sa.Column("result_payload", json_document, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(request_hash) = 64",
            name="ck_certificate_resolution_operations_request_hash",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["certificates.id"],
            name="fk_certificate_resolution_operations_certificate",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_operation_id"],
            ["certificate_resolution_operations.id"],
            name="fk_certificate_resolution_operations_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_certificate_resolution_operations_idempotency",
        ),
    )
    op.create_index(
        "ix_certificate_resolution_operations_id",
        "certificate_resolution_operations",
        ["id"],
    )
    op.create_index(
        "ix_certificate_resolution_operations_certificate_id",
        "certificate_resolution_operations",
        ["certificate_id"],
    )
    op.create_index(
        "ix_certificate_resolution_operations_source_operation_id",
        "certificate_resolution_operations",
        ["source_operation_id"],
    )
    op.create_index(
        "ix_certificate_resolution_operations_certificate_action",
        "certificate_resolution_operations",
        ["certificate_id", "operation_key"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE TRIGGER trg_certificate_resolution_operations_immutable
            BEFORE UPDATE OR DELETE
            ON certificate_resolution_operations
            FOR EACH ROW EXECUTE FUNCTION resolution_engine_prevent_mutation()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS "
            "trg_certificate_resolution_operations_immutable "
            "ON certificate_resolution_operations"
        )
    op.drop_index(
        "ix_certificate_resolution_operations_certificate_action",
        table_name="certificate_resolution_operations",
    )
    op.drop_index(
        "ix_certificate_resolution_operations_source_operation_id",
        table_name="certificate_resolution_operations",
    )
    op.drop_index(
        "ix_certificate_resolution_operations_certificate_id",
        table_name="certificate_resolution_operations",
    )
    op.drop_index(
        "ix_certificate_resolution_operations_id",
        table_name="certificate_resolution_operations",
    )
    op.drop_table("certificate_resolution_operations")
