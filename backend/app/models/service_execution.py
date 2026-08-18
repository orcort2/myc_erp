from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


SERVICE_STAGE_CATEGORIES = (
    "diagnosis",
    "repair",
    "maintenance",
    "calibration",
    "verification",
    "qualification",
    "validation",
    "training",
    "consulting",
    "sale",
    "other",
)


class ServiceUnit(IntegerPkMixin, TimestampMixin, Base):
    """Identidad operativa estable de un equipo durante toda una intervención."""

    __tablename__ = "service_units"
    __table_args__ = (
        UniqueConstraint("equipment_id", name="uq_service_units_equipment_id"),
        Index("ix_service_units_ets_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True
    )
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_work_orders.id", ondelete="RESTRICT"), index=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), index=True
    )
    origin_service_order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_order_items.id", ondelete="RESTRICT"), index=True
    )
    initial_category: Mapped[str] = mapped_column(String(40), index=True)
    evolution_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), default="Equipo")
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120), index=True)
    identification_status: Mapped[str] = mapped_column(
        String(30), default="partial", server_default="partial", index=True
    )
    identification_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), default="active", server_default="active", index=True
    )

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="service_units")
    work_order: Mapped["ServiceWorkOrder"] = relationship(back_populates="service_units")
    equipment: Mapped["Equipment | None"] = relationship(back_populates="service_unit")
    stages: Mapped[list["ServiceStage"]] = relationship(
        back_populates="service_unit",
        order_by="ServiceStage.sequence.asc()",
    )


class ServiceStage(IntegerPkMixin, TimestampMixin, Base):
    """Etapa append-only del recorrido de una unidad operativa."""

    __tablename__ = "service_stages"
    __table_args__ = (
        UniqueConstraint("service_unit_id", "sequence", name="uq_service_stage_sequence"),
        CheckConstraint(
            "category IN ('diagnosis','repair','maintenance','calibration','verification',"
            "'qualification','validation','training','consulting','sale','other')",
            name="ck_service_stages_category",
        ),
        CheckConstraint(
            "status IN ('planned','pending_quote','pending_approval','authorized','in_progress',"
            "'paused','completed','client_rejected','not_executable','exception_closed','cancelled')",
            name="ck_service_stages_status",
        ),
        Index("ix_service_stages_unit_status", "service_unit_id", "status"),
        Index("ix_service_stages_category_status", "category", "status"),
    )

    service_unit_id: Mapped[int] = mapped_column(
        ForeignKey("service_units.id", ondelete="RESTRICT"), index=True
    )
    sequence: Mapped[int] = mapped_column(index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    origin: Mapped[str] = mapped_column(String(40), index=True)
    source_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )
    quotation_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_items.id", ondelete="RESTRICT"), index=True
    )
    commercial_decision_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_item_decisions.id", ondelete="RESTRICT"), index=True
    )
    responsible_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_summary: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)

    service_unit: Mapped[ServiceUnit] = relationship(back_populates="stages")
    source_stage: Mapped["ServiceStage | None"] = relationship(
        remote_side="ServiceStage.id", foreign_keys=[source_stage_id]
    )
    responsible_user: Mapped["User | None"] = relationship(foreign_keys=[responsible_user_id])
    documents: Mapped[list["ServiceStageDocument"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class ServiceStageDocument(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_stage_documents"
    __table_args__ = (
        UniqueConstraint(
            "service_stage_id", "controlled_document_id", "document_role",
            name="uq_service_stage_document_role",
        ),
    )

    service_stage_id: Mapped[int] = mapped_column(
        ForeignKey("service_stages.id", ondelete="CASCADE"), index=True
    )
    controlled_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id", ondelete="RESTRICT"), index=True
    )
    document_role: Mapped[str] = mapped_column(String(40), default="evidence")
    external_reference: Mapped[str | None] = mapped_column(String(255))

    stage: Mapped[ServiceStage] = relationship(back_populates="documents")


class TechnicalServiceRequest(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "technical_service_requests"
    __table_args__ = (
        UniqueConstraint(
            "source_message_id", name="uq_technical_request_source_message"
        ),
        CheckConstraint(
            "status IN ('requested','quoting','quoted','partially_approved','approved','rejected','cancelled')",
            name="ck_technical_service_requests_status",
        ),
        Index("ix_technical_requests_ets_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True
    )
    service_unit_id: Mapped[int] = mapped_column(
        ForeignKey("service_units.id", ondelete="RESTRICT"), index=True
    )
    source_stage_id: Mapped[int] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_messages.id", ondelete="RESTRICT"), index=True
    )
    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="requested", server_default="requested", index=True
    )
    summary: Mapped[str] = mapped_column(Text)
    requested_categories: Mapped[list] = mapped_column(JSON, default=list)


class ServiceTask(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_tasks"
    __table_args__ = (
        UniqueConstraint("source_message_id", name="uq_service_tasks_source_message"),
        CheckConstraint(
            "status IN ('open','in_progress','completed','cancelled')",
            name="ck_service_tasks_status",
        ),
        Index("ix_service_tasks_context", "service_order_id", "service_unit_id", "service_stage_id"),
    )

    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_messages.id", ondelete="RESTRICT"), index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    service_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True
    )
    service_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_units.id", ondelete="RESTRICT"), index=True
    )
    service_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(30), default="open", server_default="open", index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignees: Mapped[list["ServiceTaskAssignee"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class ServiceTaskAssignee(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_task_assignees"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_service_task_assignee"),
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("service_tasks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    task: Mapped[ServiceTask] = relationship(back_populates="assignees")
