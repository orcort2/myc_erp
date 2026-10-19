"""Quotation revision cycle: acceptance confirmation folio and ETS archive.

Revision ID: a1b2c3d4e5f7
Revises: f9a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "f9a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "quotation_acceptances",
        sa.Column("confirmation_folio", sa.String(length=24), nullable=True),
    )
    op.create_index(
        "ix_quotation_acceptances_confirmation_folio",
        "quotation_acceptances",
        ["confirmation_folio"],
        unique=True,
    )
    # Aceptaciones históricas: folio determinista por año de aceptación.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, accepted_at FROM quotation_acceptances ORDER BY accepted_at, id")
    ).fetchall()
    counters: dict[int, int] = {}
    for row in rows:
        year = row.accepted_at.year if hasattr(row.accepted_at, "year") else int(str(row.accepted_at)[:4])
        counters[year] = counters.get(year, 0) + 1
        bind.execute(
            sa.text("UPDATE quotation_acceptances SET confirmation_folio = :f WHERE id = :i"),
            {"f": f"MYC-AC-{year}-{counters[year]:06d}", "i": row.id},
        )
    for year, last in counters.items():
        bind.execute(
            sa.text(
                "INSERT INTO institutional_folio_sequences "
                "(document_type, prefix, year, next_value, created_at, updated_at) "
                "VALUES ('quotation_acceptance', 'MYC-AC', :y, :n, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"y": year, "n": last + 1},
        )

    op.create_table(
        "service_order_archives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_service_order_id", sa.Integer(), nullable=False),
        sa.Column("service_order_folio", sa.String(length=40), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quotation_folio", sa.String(length=40), nullable=False),
        sa.Column("accepted_snapshot_id", sa.Integer(), sa.ForeignKey("quotation_snapshots.id", ondelete="RESTRICT")),
        sa.Column("accepted_snapshot_number", sa.Integer()),
        sa.Column("acceptance_id", sa.Integer(), sa.ForeignKey("quotation_acceptances.id", ondelete="RESTRICT")),
        sa.Column("previous_status", sa.String(length=60), nullable=False),
        sa.Column("source_snapshot", sa.JSON()),
        sa.Column("archive_data", sa.JSON(), nullable=False),
        sa.Column(
            "exception_request_id",
            sa.Integer(),
            sa.ForeignKey("quotation_service_change_requests.id", ondelete="RESTRICT"),
        ),
        sa.Column("exception_folio", sa.String(length=40)),
        sa.Column("deleted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("integrity_hash", sa.String(length=64), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True)),
        sa.Column("restored_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("restoration_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("exception_request_id", name="uq_service_order_archives_exception"),
    )
    for column in (
        "original_service_order_id",
        "service_order_folio",
        "quotation_id",
        "accepted_snapshot_id",
        "acceptance_id",
        "exception_request_id",
        "exception_folio",
        "deleted_by_id",
        "restored_by_id",
    ):
        op.create_index(f"ix_service_order_archives_{column}", "service_order_archives", [column])


def downgrade():
    op.drop_table("service_order_archives")
    op.execute("DELETE FROM institutional_folio_sequences WHERE document_type = 'quotation_acceptance'")
    op.drop_index("ix_quotation_acceptances_confirmation_folio", table_name="quotation_acceptances")
    op.drop_column("quotation_acceptances", "confirmation_folio")
