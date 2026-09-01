"""version and freeze field sheet PDFs

Revision ID: b71d4a9f2c18
Revises: a3983f9a6ca9
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b71d4a9f2c18"
down_revision: Union[str, None] = "a3983f9a6ca9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("field_sheets", sa.Column("pdf_renderer_key", sa.String(100), nullable=True))
    op.add_column("field_sheets", sa.Column("pdf_renderer_version", sa.Integer(), nullable=True))
    op.add_column("field_sheets", sa.Column("final_pdf_path", sa.Text(), nullable=True))
    op.add_column("field_sheets", sa.Column("final_pdf_sha256", sa.String(64), nullable=True))
    op.add_column(
        "field_sheets",
        sa.Column("final_pdf_template_definition_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "field_sheets",
        sa.Column("final_pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Only backfill a renderer identity when the historical snapshot
    # unambiguously names it. Anything else (missing snapshot, unknown
    # pdf_template) stays NULL/NULL rather than being guessed at -- a
    # fabricated renderer identity for a row we can't actually reproduce is
    # worse than an explicit "unknown", which resolve_field_sheet_pdf_renderer
    # now surfaces as a clear conflict instead of silently rendering it.
    op.execute(
        """
        UPDATE field_sheets
        SET pdf_renderer_key = CASE
            WHEN COALESCE(template_definition_json ->> 'pdf_template', '') = 'field_sheet_engine_pdf.html'
                THEN 'field_sheet_engine'
            WHEN COALESCE(template_definition_json ->> 'pdf_template', '') IN (
                'field_sheet_general_pdf.html',
                'field_sheet_anemometer_pdf.html',
                'field_sheet_electrical_pdf.html'
            ) THEN 'legacy:' || (template_definition_json ->> 'pdf_template')
            ELSE NULL
        END,
        pdf_renderer_version = CASE
            WHEN COALESCE(template_definition_json ->> 'pdf_template', '') = 'field_sheet_engine_pdf.html'
                THEN 1
            WHEN COALESCE(template_definition_json ->> 'pdf_template', '') IN (
                'field_sheet_general_pdf.html',
                'field_sheet_anemometer_pdf.html',
                'field_sheet_electrical_pdf.html'
            ) THEN 1
            ELSE NULL
        END
        """
    )


def downgrade() -> None:
    op.drop_column("field_sheets", "final_pdf_generated_at")
    op.drop_column("field_sheets", "final_pdf_template_definition_version")
    op.drop_column("field_sheets", "final_pdf_sha256")
    op.drop_column("field_sheets", "final_pdf_path")
    op.drop_column("field_sheets", "pdf_renderer_version")
    op.drop_column("field_sheets", "pdf_renderer_key")
