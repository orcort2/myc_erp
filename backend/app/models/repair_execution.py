from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class RepairExecution(IntegerPkMixin, TimestampMixin, Base):
    """Expediente estructurado de Reparación sobre una ServiceUnit estable.

    Espejo arquitectónico de MaintenanceExecution (app/models/maintenance_execution.py).
    Fase 1: SOLO laboratorio. No existe location_mode/field_address como en Mantenimiento
    porque el modo de campo está explícitamente fuera de alcance en esta fase.
    """

    __tablename__ = "repair_executions"
    __table_args__ = (
        UniqueConstraint("service_unit_id", name="uq_repair_execution_unit"),
        UniqueConstraint("service_stage_id", name="uq_repair_execution_stage"),
        CheckConstraint(
            "origin IN ('quotation','maintenance_linked')",
            name="ck_repair_origin",
        ),
        CheckConstraint(
            "status IN ('pending_arrival','pending_assignment','assigned','in_evaluation',"
            "'in_repair','testing','technically_completed','equipment_not_suitable',"
            "'pending_release','closed','cancelled')",
            name="ck_repair_status",
        ),
        CheckConstraint(
            "conclusion IS NULL OR conclusion IN ('repaired','equipment_not_suitable')",
            name="ck_repair_conclusion",
        ),
        Index("ix_repair_execution_order_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True)
    service_order_item_id: Mapped[int] = mapped_column(ForeignKey("service_order_items.id", ondelete="RESTRICT"), index=True)
    service_unit_id: Mapped[int] = mapped_column(ForeignKey("service_units.id", ondelete="RESTRICT"), index=True)
    service_stage_id: Mapped[int] = mapped_column(ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True)

    # Decisión funcional #1: origen/trazabilidad. 'quotation' cuando la unidad nace
    # directamente de una cotización con partidas operational_category='repair';
    # 'maintenance_linked' cuando proviene de un MaintenanceChangeRequest
    # (change_type='repair', decision='linked') resuelto sobre un ETS de Mantenimiento.
    origin: Mapped[str] = mapped_column(String(30), index=True)
    source_maintenance_change_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_change_requests.id", ondelete="RESTRICT"), index=True
    )

    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="pending_arrival", server_default="pending_arrival", index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    # Decisión funcional #3:
    # El diagnóstico continúa siendo opcional y no bloquea el avance.
    # La información técnicamente explotable se conserva estructurada,
    # mientras diagnosis_notes mantiene la narrativa libre y compatibilidad
    # con consumidores anteriores.
    diagnosis_data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    diagnosis_notes: Mapped[str | None] = mapped_column(
        Text,
    )

    diagnosis_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Decisión funcional #4: conclusión 'equipment_not_suitable' exige justificación
    # y salta reparación/pruebas.
    conclusion: Mapped[str | None] = mapped_column(String(30))
    conclusion_reason: Mapped[str | None] = mapped_column(Text)

    technical_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report_status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    report_version: Mapped[int] = mapped_column(default=0, server_default="0")
    report_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_report_version: Mapped[int | None] = mapped_column()
    signer_name: Mapped[str | None] = mapped_column(String(180))
    signature_data_url: Mapped[str | None] = mapped_column(Text)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_decision: Mapped[str | None] = mapped_column(String(30))

    # Decisión funcional #9: SLA ~14 días como alerta suave (notice), no bloqueante duro.
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Decisión funcional #12: ciclos de reapertura de garantía preparables. El cierre
    # histórico original NUNCA se sobrescribe.
    warranty_reopened_count: Mapped[int] = mapped_column(default=0, server_default="0")
    original_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Decisión funcional #13: cancelación antes/después de la primera intervención.
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_after_intervention: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    # Decisión funcional #11: vínculo a Calibración preparable, NO ejecutado en Fase 1.
    linked_calibration_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    service_unit: Mapped["ServiceUnit"] = relationship(foreign_keys=[service_unit_id])
    service_stage: Mapped["ServiceStage"] = relationship(foreign_keys=[service_stage_id])
    technician: Mapped["User | None"] = relationship(foreign_keys=[technician_id])
    pauses: Mapped[list["RepairPause"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="RepairPause.id")
    interventions: Mapped[list["RepairIntervention"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="RepairIntervention.sequence")
    tests: Mapped[list["RepairTest"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="RepairTest.sequence")
    changes: Mapped[list["RepairChangeRequest"]] = relationship(back_populates="execution", cascade="all, delete-orphan", order_by="RepairChangeRequest.id")


class RepairIntervention(IntegerPkMixin, TimestampMixin, Base):
    """Registro append-only de una intervención técnica (Decisión #6: N intervenciones)."""

    __tablename__ = "repair_interventions"
    __table_args__ = (
        UniqueConstraint("repair_execution_id", "sequence", name="uq_repair_intervention_sequence"),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('effective','partial','ineffective')",
            name="ck_repair_intervention_outcome",
        ),
    )

    repair_execution_id: Mapped[int] = mapped_column(ForeignKey("repair_executions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(index=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    description: Mapped[str] = mapped_column(Text)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    # Decisión funcional #7: componentes removidos, default return_to_client.
    removed_components: Mapped[list] = mapped_column(JSON, default=list)
    outcome: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    execution: Mapped[RepairExecution] = relationship(back_populates="interventions")


class RepairTest(IntegerPkMixin, TimestampMixin, Base):
    """Registro de pruebas técnicas, con ciclo intervención<->prueba (Decisión #10)."""

    __tablename__ = "repair_tests"
    __table_args__ = (
        UniqueConstraint("repair_execution_id", "sequence", name="uq_repair_test_sequence"),
        CheckConstraint("result IN ('pass','fail','inconclusive')", name="ck_repair_test_result"),
    )

    repair_execution_id: Mapped[int] = mapped_column(ForeignKey("repair_executions.id", ondelete="CASCADE"), index=True)
    intervention_id: Mapped[int | None] = mapped_column(ForeignKey("repair_interventions.id", ondelete="RESTRICT"), index=True)
    sequence: Mapped[int] = mapped_column(index=True)
    test_type: Mapped[str] = mapped_column(String(60))
    result: Mapped[str] = mapped_column(String(20), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    performed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    execution: Mapped[RepairExecution] = relationship(back_populates="tests")


class RepairPause(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "repair_pauses"
    __table_args__ = (
        CheckConstraint(
            "pause_type IN ("
            "'spare_part',"
            "'authorization',"
            "'client_decision',"
            "'administrative_investigation',"
            "'warehouse'"
            ")",
            name="ck_repair_pause_type",
        ),
        CheckConstraint("status IN ('active','resolved')", name="ck_repair_pause_status"),
    )

    repair_execution_id: Mapped[int] = mapped_column(ForeignKey("repair_executions.id", ondelete="CASCADE"), index=True)
    pause_type: Mapped[str] = mapped_column(String(40), index=True)
    reason: Mapped[str] = mapped_column(Text)
    responsible_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    tentative_resume_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    execution: Mapped[RepairExecution] = relationship(back_populates="pauses")


class RepairChangeRequest(IntegerPkMixin, TimestampMixin, Base):
    """Solicitudes de cambio de alcance. Espejo de MaintenanceChangeRequest.

    Decisión funcional #5: la autorización de alcance adicional queda aplazada
    en su ejecución comercial completa, pero el contrato de datos (quotation_item_id)
    debe estar preparado. Decisión funcional #14: equipo peor de lo recibido dispara
    investigación administrativa reutilizando el patrón de Mantenimiento
    (change_type='investigation', decision='linked').
    """

    __tablename__ = "repair_change_requests"
    __table_args__ = (
        CheckConstraint("change_type IN ('additional_scope','investigation')", name="ck_repair_change_type"),
        CheckConstraint("status IN ('requested','approved','rejected','linked')", name="ck_repair_change_status"),
    )

    repair_execution_id: Mapped[int] = mapped_column(ForeignKey("repair_executions.id", ondelete="CASCADE"), index=True)
    change_type: Mapped[str] = mapped_column(String(30), index=True)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="requested", server_default="requested", index=True)
    quotation_item_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_items.id", ondelete="RESTRICT"), index=True)
    linked_service_order_id: Mapped[int | None] = mapped_column(ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    execution: Mapped[RepairExecution] = relationship(back_populates="changes")
