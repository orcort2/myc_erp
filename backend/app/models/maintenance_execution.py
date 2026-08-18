from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class MaintenanceExecution(IntegerPkMixin, TimestampMixin, Base):
    """Expediente estructurado de Mantenimiento sobre una ServiceUnit estable."""

    __tablename__ = "maintenance_executions"
    __table_args__ = (
        UniqueConstraint("service_unit_id", name="uq_maintenance_execution_unit"),
        UniqueConstraint("service_stage_id", name="uq_maintenance_execution_stage"),
        CheckConstraint("maintenance_type IN ('preventive','corrective')", name="ck_maintenance_type"),
        CheckConstraint("location_mode IN ('laboratory','field')", name="ck_maintenance_location"),
        Index("ix_maintenance_execution_order_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True)
    service_order_item_id: Mapped[int] = mapped_column(ForeignKey("service_order_items.id", ondelete="RESTRICT"), index=True)
    service_unit_id: Mapped[int] = mapped_column(ForeignKey("service_units.id", ondelete="RESTRICT"), index=True)
    service_stage_id: Mapped[int] = mapped_column(ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True)
    maintenance_type: Mapped[str] = mapped_column(String(20), index=True)
    location_mode: Mapped[str] = mapped_column(String(20), index=True)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="pending_arrival", server_default="pending_arrival", index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    field_request_status: Mapped[str | None] = mapped_column(String(30), index=True)
    field_address: Mapped[dict | None] = mapped_column(JSON)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_condition: Mapped[str | None] = mapped_column(String(40))
    initial_description: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    final_condition: Mapped[str | None] = mapped_column(String(50))
    functional_result: Mapped[str | None] = mapped_column(Text)
    technical_conclusion: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    before_photos: Mapped[list] = mapped_column(JSON, default=list)
    after_photos: Mapped[list] = mapped_column(JSON, default=list)
    technical_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    report_version: Mapped[int] = mapped_column(default=0, server_default="0")
    report_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_report_version: Mapped[int | None] = mapped_column()
    signer_name: Mapped[str | None] = mapped_column(String(180))
    signature_data_url: Mapped[str | None] = mapped_column(Text)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_decision: Mapped[str | None] = mapped_column(String(30))
    investigation_status: Mapped[str | None] = mapped_column(String(30), index=True)
    linked_investigation_stage_id: Mapped[int | None] = mapped_column(ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    service_unit: Mapped["ServiceUnit"] = relationship(foreign_keys=[service_unit_id])
    service_stage: Mapped["ServiceStage"] = relationship(foreign_keys=[service_stage_id])
    technician: Mapped["User | None"] = relationship(foreign_keys=[technician_id])
    pauses: Mapped[list["MaintenancePause"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="MaintenancePause.id")
    materials: Mapped[list["MaintenanceMaterial"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="MaintenanceMaterial.id")
    changes: Mapped[list["MaintenanceChangeRequest"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="MaintenanceChangeRequest.id")


class MaintenancePause(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_pauses"
    __table_args__ = (
        CheckConstraint("pause_type IN ('spare_part','authorization','second_intervention','commercial_review','administrative_investigation')", name="ck_maintenance_pause_type"),
        CheckConstraint("status IN ('active','resolved')", name="ck_maintenance_pause_status"),
    )

    maintenance_execution_id: Mapped[int] = mapped_column(ForeignKey("maintenance_executions.id", ondelete="CASCADE"), index=True)
    pause_type: Mapped[str] = mapped_column(String(40), index=True)
    reason: Mapped[str] = mapped_column(Text)
    responsible_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    tentative_resume_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution: Mapped[MaintenanceExecution] = relationship(back_populates="pauses")


class MaintenanceMaterial(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_materials"
    __table_args__ = (
        CheckConstraint("material_type IN ('used','required')", name="ck_maintenance_material_type"),
        CheckConstraint("quantity > 0", name="ck_maintenance_material_quantity"),
    )

    maintenance_execution_id: Mapped[int] = mapped_column(ForeignKey("maintenance_executions.id", ondelete="CASCADE"), index=True)
    material_type: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(180))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit: Mapped[str] = mapped_column(String(40))
    component: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)
    internal_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    decision: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(30), default="technician", server_default="technician")
    execution: Mapped[MaintenanceExecution] = relationship(back_populates="materials")


class MaintenanceChangeRequest(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_change_requests"
    __table_args__ = (
        CheckConstraint("change_type IN ('corrective','repair','investigation')", name="ck_maintenance_change_type"),
        CheckConstraint("status IN ('requested','approved','rejected','overridden','linked')", name="ck_maintenance_change_status"),
    )

    maintenance_execution_id: Mapped[int] = mapped_column(ForeignKey("maintenance_executions.id", ondelete="CASCADE"), index=True)
    change_type: Mapped[str] = mapped_column(String(30), index=True)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="requested", server_default="requested", index=True)
    quotation_item_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_items.id", ondelete="RESTRICT"), index=True)
    linked_service_order_id: Mapped[int | None] = mapped_column(ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution: Mapped[MaintenanceExecution] = relationship(back_populates="changes")
