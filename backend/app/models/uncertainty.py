from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class UncertaintyModel(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uncertainty_models"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_uncertainty_models_code_version"),
    )

    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    magnitude: Mapped[str] = mapped_column(String(80), index=True)
    equipment_family: Mapped[str | None] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40), default="1.0", index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    default_coverage_factor: Mapped[float] = mapped_column(default=2.0)
    notes: Mapped[str | None] = mapped_column(Text)

    versions: Mapped[list["UncertaintyModelVersion"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="UncertaintyModelVersion.created_at.desc(), UncertaintyModelVersion.id.desc()",
    )
    components: Mapped[list["UncertaintyComponent"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="UncertaintyComponent.sort_order.asc(), UncertaintyComponent.id.asc()",
    )
    formulas: Mapped[list["UncertaintyFormula"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="UncertaintyFormula.sort_order.asc(), UncertaintyFormula.id.asc()",
    )
    exceptions: Mapped[list["UncertaintyModelException"]] = relationship(
        back_populates="alternate_model",
        cascade="all, delete-orphan",
        foreign_keys="UncertaintyModelException.alternate_model_id",
    )
    calculations: Mapped[list["UncertaintyCalculation"]] = relationship(back_populates="model")


class UncertaintyModelVersion(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uncertainty_model_versions"
    __table_args__ = (
        UniqueConstraint("model_id", "version_number", name="uq_uncertainty_model_versions_number"),
    )

    model_id: Mapped[int] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    version_number: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    change_summary: Mapped[str | None] = mapped_column(Text)
    default_coverage_factor: Mapped[float] = mapped_column(default=2.0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    obsolete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    model: Mapped["UncertaintyModel"] = relationship(back_populates="versions")
    components: Mapped[list["UncertaintyComponent"]] = relationship(
        back_populates="model_version",
        cascade="all, delete-orphan",
        order_by="UncertaintyComponent.sort_order.asc(), UncertaintyComponent.id.asc()",
    )
    formulas: Mapped[list["UncertaintyFormula"]] = relationship(
        back_populates="model_version",
        cascade="all, delete-orphan",
        order_by="UncertaintyFormula.sort_order.asc(), UncertaintyFormula.id.asc()",
    )
    calculations: Mapped[list["UncertaintyCalculation"]] = relationship(back_populates="model_version")


class UncertaintyComponent(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uncertainty_components"

    model_id: Mapped[int] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("uncertainty_model_versions.id"), index=True
    )
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(60), index=True)
    distribution: Mapped[str | None] = mapped_column(String(60))
    divisor: Mapped[float | None] = mapped_column(default=None)
    sensitivity_coefficient: Mapped[float] = mapped_column(default=1.0)
    value_expression: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    model: Mapped["UncertaintyModel"] = relationship(back_populates="components")
    model_version: Mapped["UncertaintyModelVersion | None"] = relationship(back_populates="components")


class UncertaintyFormula(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uncertainty_formulas"

    model_id: Mapped[int] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("uncertainty_model_versions.id"), index=True
    )
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    expression: Mapped[str] = mapped_column(Text)
    result_key: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active_formula: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    model: Mapped["UncertaintyModel"] = relationship(back_populates="formulas")
    model_version: Mapped["UncertaintyModelVersion | None"] = relationship(back_populates="formulas")


class UncertaintyModelException(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uncertainty_model_exceptions"

    base_model_id: Mapped[int | None] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    alternate_model_id: Mapped[int] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    base_model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("uncertainty_model_versions.id"), index=True
    )
    alternate_model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("uncertainty_model_versions.id"), index=True
    )
    magnitude: Mapped[str | None] = mapped_column(String(80), index=True)
    equipment_type: Mapped[str | None] = mapped_column(String(180), index=True)
    equipment_model: Mapped[str | None] = mapped_column(String(120), index=True)
    procedure_id: Mapped[int | None] = mapped_column(ForeignKey("calibration_procedures.id"), index=True)
    profile_key: Mapped[str | None] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(Text)
    authorized_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)

    base_model: Mapped["UncertaintyModel | None"] = relationship(
        foreign_keys=[base_model_id],
    )
    alternate_model: Mapped["UncertaintyModel"] = relationship(
        back_populates="exceptions",
        foreign_keys=[alternate_model_id],
    )
    base_model_version: Mapped["UncertaintyModelVersion | None"] = relationship(
        foreign_keys=[base_model_version_id],
    )
    alternate_model_version: Mapped["UncertaintyModelVersion | None"] = relationship(
        foreign_keys=[alternate_model_version_id],
    )


class UncertaintyCalculation(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "uncertainty_calculations"

    field_sheet_id: Mapped[int] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    uncertainty_model_id: Mapped[int] = mapped_column(ForeignKey("uncertainty_models.id"), index=True)
    uncertainty_model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("uncertainty_model_versions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="calculated", index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    calculation_snapshot: Mapped[dict] = mapped_column(JSON)
    input_snapshot: Mapped[dict] = mapped_column(JSON)
    component_results: Mapped[list] = mapped_column(JSON)
    formula_results: Mapped[dict] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[list] = mapped_column(JSON, default=list)

    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="uncertainty_calculations")
    model: Mapped["UncertaintyModel"] = relationship(back_populates="calculations")
    model_version: Mapped["UncertaintyModelVersion | None"] = relationship(back_populates="calculations")
