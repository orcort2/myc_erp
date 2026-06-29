"""external certificate pdf flow

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-29 15:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("certificates", sa.Column("expected_folio", sa.String(length=40), nullable=True))
    op.add_column("certificates", sa.Column("final_pdf_path", sa.String(length=255), nullable=True))
    op.add_column("certificates", sa.Column("final_pdf_original_filename", sa.String(length=255), nullable=True))
    op.add_column("certificates", sa.Column("final_pdf_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("final_pdf_uploaded_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("capture_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("capture_started_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("sent_to_quality_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("sent_to_quality_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("quality_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("quality_reviewed_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("quality_rejection_reason", sa.Text(), nullable=True))
    op.add_column("certificates", sa.Column("released_to_client_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("released_to_client_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("external_source", sa.String(length=40), nullable=False, server_default="excel"))
    op.add_column("certificates", sa.Column("match_status", sa.String(length=40), nullable=False, server_default="pending"))
    op.add_column("certificates", sa.Column("match_details", sa.JSON(), nullable=True))
    op.add_column("certificates", sa.Column("client_visible", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute("UPDATE certificates SET expected_folio = folio WHERE expected_folio IS NULL")
    op.execute(
        """
        UPDATE certificates
        SET status = CASE status
            WHEN 'generated' THEN 'capture_in_progress'
            WHEN 'correction_requested' THEN 'quality_rejected'
            WHEN 'approved' THEN 'quality_approved'
            WHEN 'released' THEN 'released_to_client'
            ELSE status
        END
        """
    )
    op.execute("UPDATE certificates SET client_visible = true WHERE status = 'released_to_client'")

    op.create_index(op.f("ix_certificates_expected_folio"), "certificates", ["expected_folio"], unique=True)
    op.create_index(op.f("ix_certificates_final_pdf_uploaded_by_id"), "certificates", ["final_pdf_uploaded_by_id"], unique=False)
    op.create_index(op.f("ix_certificates_capture_started_by_id"), "certificates", ["capture_started_by_id"], unique=False)
    op.create_index(op.f("ix_certificates_sent_to_quality_by_id"), "certificates", ["sent_to_quality_by_id"], unique=False)
    op.create_index(op.f("ix_certificates_quality_reviewed_by_id"), "certificates", ["quality_reviewed_by_id"], unique=False)
    op.create_index(op.f("ix_certificates_released_to_client_by_id"), "certificates", ["released_to_client_by_id"], unique=False)
    op.create_index(op.f("ix_certificates_external_source"), "certificates", ["external_source"], unique=False)
    op.create_index(op.f("ix_certificates_match_status"), "certificates", ["match_status"], unique=False)
    op.create_index(op.f("ix_certificates_client_visible"), "certificates", ["client_visible"], unique=False)
    op.create_foreign_key("fk_certificates_final_pdf_uploaded_by_id", "certificates", "users", ["final_pdf_uploaded_by_id"], ["id"])
    op.create_foreign_key("fk_certificates_capture_started_by_id", "certificates", "users", ["capture_started_by_id"], ["id"])
    op.create_foreign_key("fk_certificates_sent_to_quality_by_id", "certificates", "users", ["sent_to_quality_by_id"], ["id"])
    op.create_foreign_key("fk_certificates_quality_reviewed_by_id", "certificates", "users", ["quality_reviewed_by_id"], ["id"])
    op.create_foreign_key("fk_certificates_released_to_client_by_id", "certificates", "users", ["released_to_client_by_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_certificates_released_to_client_by_id", "certificates", type_="foreignkey")
    op.drop_constraint("fk_certificates_quality_reviewed_by_id", "certificates", type_="foreignkey")
    op.drop_constraint("fk_certificates_sent_to_quality_by_id", "certificates", type_="foreignkey")
    op.drop_constraint("fk_certificates_capture_started_by_id", "certificates", type_="foreignkey")
    op.drop_constraint("fk_certificates_final_pdf_uploaded_by_id", "certificates", type_="foreignkey")
    op.drop_index(op.f("ix_certificates_client_visible"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_match_status"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_external_source"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_released_to_client_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_quality_reviewed_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_sent_to_quality_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_capture_started_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_final_pdf_uploaded_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_expected_folio"), table_name="certificates")
    op.drop_column("certificates", "client_visible")
    op.drop_column("certificates", "match_details")
    op.drop_column("certificates", "match_status")
    op.drop_column("certificates", "external_source")
    op.drop_column("certificates", "released_to_client_by_id")
    op.drop_column("certificates", "released_to_client_at")
    op.drop_column("certificates", "quality_rejection_reason")
    op.drop_column("certificates", "quality_reviewed_by_id")
    op.drop_column("certificates", "quality_reviewed_at")
    op.drop_column("certificates", "sent_to_quality_by_id")
    op.drop_column("certificates", "sent_to_quality_at")
    op.drop_column("certificates", "capture_started_by_id")
    op.drop_column("certificates", "capture_started_at")
    op.drop_column("certificates", "final_pdf_uploaded_by_id")
    op.drop_column("certificates", "final_pdf_uploaded_at")
    op.drop_column("certificates", "final_pdf_original_filename")
    op.drop_column("certificates", "final_pdf_path")
    op.drop_column("certificates", "expected_folio")
