"""version uncertainty models

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-29 14:20:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "uncertainty_model_versions",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("default_coverage_factor", sa.Float(), nullable=False, server_default="2"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("obsolete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["uncertainty_models.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "version_number", name="uq_uncertainty_model_versions_number"),
    )
    op.create_index(op.f("ix_uncertainty_model_versions_approved_by_id"), "uncertainty_model_versions", ["approved_by_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_versions_model_id"), "uncertainty_model_versions", ["model_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_versions_status"), "uncertainty_model_versions", ["status"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_versions_submitted_by_id"), "uncertainty_model_versions", ["submitted_by_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_versions_version_number"), "uncertainty_model_versions", ["version_number"], unique=False)

    op.add_column("uncertainty_components", sa.Column("model_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_uncertainty_components_model_version_id"), "uncertainty_components", ["model_version_id"], unique=False)
    op.create_foreign_key(
        "fk_uncertainty_components_model_version_id",
        "uncertainty_components",
        "uncertainty_model_versions",
        ["model_version_id"],
        ["id"],
    )
    op.add_column("uncertainty_formulas", sa.Column("model_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_uncertainty_formulas_model_version_id"), "uncertainty_formulas", ["model_version_id"], unique=False)
    op.create_foreign_key(
        "fk_uncertainty_formulas_model_version_id",
        "uncertainty_formulas",
        "uncertainty_model_versions",
        ["model_version_id"],
        ["id"],
    )
    op.add_column("calibration_procedures", sa.Column("uncertainty_model_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_calibration_procedures_uncertainty_model_version_id"), "calibration_procedures", ["uncertainty_model_version_id"], unique=False)
    op.create_foreign_key(
        "fk_calibration_procedures_uncertainty_model_version_id",
        "calibration_procedures",
        "uncertainty_model_versions",
        ["uncertainty_model_version_id"],
        ["id"],
    )
    op.add_column("uncertainty_model_exceptions", sa.Column("base_model_version_id", sa.Integer(), nullable=True))
    op.add_column("uncertainty_model_exceptions", sa.Column("alternate_model_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_uncertainty_model_exceptions_base_model_version_id"), "uncertainty_model_exceptions", ["base_model_version_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_alternate_model_version_id"), "uncertainty_model_exceptions", ["alternate_model_version_id"], unique=False)
    op.create_foreign_key(
        "fk_uncertainty_model_exceptions_base_model_version_id",
        "uncertainty_model_exceptions",
        "uncertainty_model_versions",
        ["base_model_version_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_uncertainty_model_exceptions_alternate_model_version_id",
        "uncertainty_model_exceptions",
        "uncertainty_model_versions",
        ["alternate_model_version_id"],
        ["id"],
    )
    op.add_column("uncertainty_calculations", sa.Column("uncertainty_model_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_uncertainty_calculations_uncertainty_model_version_id"), "uncertainty_calculations", ["uncertainty_model_version_id"], unique=False)
    op.create_foreign_key(
        "fk_uncertainty_calculations_uncertainty_model_version_id",
        "uncertainty_calculations",
        "uncertainty_model_versions",
        ["uncertainty_model_version_id"],
        ["id"],
    )

    op.execute(
        """
        INSERT INTO uncertainty_model_versions (
            model_id,
            version_number,
            status,
            change_summary,
            default_coverage_factor,
            created_at,
            updated_at,
            is_active
        )
        SELECT
            id,
            version,
            CASE WHEN status = 'active' THEN 'approved' ELSE status END,
            'Version inicial migrada desde uncertainty_models',
            default_coverage_factor,
            created_at,
            updated_at,
            is_active
        FROM uncertainty_models
        WHERE NOT EXISTS (
            SELECT 1
            FROM uncertainty_model_versions
            WHERE uncertainty_model_versions.model_id = uncertainty_models.id
              AND uncertainty_model_versions.version_number = uncertainty_models.version
        )
        """
    )
    op.execute(
        """
        UPDATE uncertainty_components
        SET model_version_id = uncertainty_model_versions.id
        FROM uncertainty_model_versions
        WHERE uncertainty_components.model_id = uncertainty_model_versions.model_id
          AND uncertainty_components.model_version_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE uncertainty_formulas
        SET model_version_id = uncertainty_model_versions.id
        FROM uncertainty_model_versions
        WHERE uncertainty_formulas.model_id = uncertainty_model_versions.model_id
          AND uncertainty_formulas.model_version_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE calibration_procedures
        SET uncertainty_model_version_id = uncertainty_model_versions.id
        FROM uncertainty_model_versions
        WHERE calibration_procedures.uncertainty_model_id = uncertainty_model_versions.model_id
          AND uncertainty_model_versions.status = 'approved'
          AND calibration_procedures.uncertainty_model_version_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE uncertainty_calculations
        SET uncertainty_model_version_id = uncertainty_model_versions.id
        FROM uncertainty_model_versions
        WHERE uncertainty_calculations.uncertainty_model_id = uncertainty_model_versions.model_id
          AND uncertainty_calculations.uncertainty_model_version_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE uncertainty_model_exceptions
        SET alternate_model_version_id = uncertainty_model_versions.id
        FROM uncertainty_model_versions
        WHERE uncertainty_model_exceptions.alternate_model_id = uncertainty_model_versions.model_id
          AND uncertainty_model_versions.status = 'approved'
          AND uncertainty_model_exceptions.alternate_model_version_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_uncertainty_calculations_uncertainty_model_version_id", "uncertainty_calculations", type_="foreignkey")
    op.drop_index(op.f("ix_uncertainty_calculations_uncertainty_model_version_id"), table_name="uncertainty_calculations")
    op.drop_column("uncertainty_calculations", "uncertainty_model_version_id")
    op.drop_constraint("fk_uncertainty_model_exceptions_alternate_model_version_id", "uncertainty_model_exceptions", type_="foreignkey")
    op.drop_constraint("fk_uncertainty_model_exceptions_base_model_version_id", "uncertainty_model_exceptions", type_="foreignkey")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_alternate_model_version_id"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_base_model_version_id"), table_name="uncertainty_model_exceptions")
    op.drop_column("uncertainty_model_exceptions", "alternate_model_version_id")
    op.drop_column("uncertainty_model_exceptions", "base_model_version_id")
    op.drop_constraint("fk_calibration_procedures_uncertainty_model_version_id", "calibration_procedures", type_="foreignkey")
    op.drop_index(op.f("ix_calibration_procedures_uncertainty_model_version_id"), table_name="calibration_procedures")
    op.drop_column("calibration_procedures", "uncertainty_model_version_id")
    op.drop_constraint("fk_uncertainty_formulas_model_version_id", "uncertainty_formulas", type_="foreignkey")
    op.drop_index(op.f("ix_uncertainty_formulas_model_version_id"), table_name="uncertainty_formulas")
    op.drop_column("uncertainty_formulas", "model_version_id")
    op.drop_constraint("fk_uncertainty_components_model_version_id", "uncertainty_components", type_="foreignkey")
    op.drop_index(op.f("ix_uncertainty_components_model_version_id"), table_name="uncertainty_components")
    op.drop_column("uncertainty_components", "model_version_id")
    op.drop_index(op.f("ix_uncertainty_model_versions_version_number"), table_name="uncertainty_model_versions")
    op.drop_index(op.f("ix_uncertainty_model_versions_submitted_by_id"), table_name="uncertainty_model_versions")
    op.drop_index(op.f("ix_uncertainty_model_versions_status"), table_name="uncertainty_model_versions")
    op.drop_index(op.f("ix_uncertainty_model_versions_model_id"), table_name="uncertainty_model_versions")
    op.drop_index(op.f("ix_uncertainty_model_versions_approved_by_id"), table_name="uncertainty_model_versions")
    op.drop_table("uncertainty_model_versions")
