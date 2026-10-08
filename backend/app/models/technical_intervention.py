from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class TechnicalIntervention(IntegerPkMixin, TimestampMixin, Base):
    """Intervención técnica individual sobre un equipo de OT (SG-4J-A1).

    Es la IDENTIDAD estable de un trabajo técnico (p. ej. una instalación):
    su folio institucional y su equipo no cambian aunque el documento que la
    respalda tenga varias revisiones (`TechnicalReport.revision_number`).
    Un mismo equipo puede tener varias intervenciones, incluso del mismo tipo;
    esa capacidad aún NO está habilitada funcionalmente (hoy el flujo crea
    exactamente una por reporte, de forma transparente).

    El folio institucional pertenece a la intervención. Hoy cada reporte
    conserva además su propia copia (`TechnicalReport.folio`, única) para no
    romper a ningún consumidor; las revisiones futuras reutilizarán el folio de
    la intervención cuando esa restricción heredada se retire (migración
    posterior, ver SG-4J-A2).
    """

    __tablename__ = "technical_interventions"
    __table_args__ = (
        CheckConstraint(
            "intervention_type IN "
            "('installation', 'verification', 'repair', 'maintenance', 'sale')",
            name="ck_technical_intervention_type",
        ),
        CheckConstraint(
            "status IN ('open', 'completed', 'cancelled')",
            name="ck_technical_intervention_status",
        ),
        UniqueConstraint("folio", name="uq_technical_interventions_folio"),
        Index("ix_technical_interventions_lab_equipment_id", "lab_equipment_id"),
        Index("ix_technical_interventions_intervention_type", "intervention_type"),
        Index("ix_technical_interventions_status", "status"),
        Index("ix_technical_interventions_created_by_user_id", "created_by_user_id"),
    )

    lab_equipment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lab_work_order_equipment.id",
            name="fk_technical_interventions_lab_equipment_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    intervention_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # Folio institucional (MYC-INMM-AA-XXXX para instalación).
    folio: Mapped[str] = mapped_column(String(40), nullable=False)
    # Estado OPERATIVO de la intervención (no el del documento):
    # open -> trabajo en curso o pendiente de documento final; completed ->
    # documento final vigente completado; cancelled.
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="open", server_default="open"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_technical_interventions_created_by_user_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    lab_equipment: Mapped["LabWorkOrderEquipment"] = relationship(
        foreign_keys=[lab_equipment_id],
    )
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])
    reports: Mapped[list["TechnicalReport"]] = relationship(
        back_populates="intervention",
        order_by="TechnicalReport.revision_number",
        lazy="selectin",
    )
    delivery_links: Mapped[list["TechnicalInterventionDelivery"]] = relationship(
        back_populates="intervention",
        order_by="TechnicalInterventionDelivery.id",
    )

    @property
    def current_report(self) -> "TechnicalReport | None":
        return next((report for report in self.reports if report.is_current), None)


class TechnicalInterventionDelivery(IntegerPkMixin, TimestampMixin, Base):
    """Asociación entre una intervención y una entrega física.

    - Varias intervenciones pueden estar respaldadas por una misma entrega
      (varias filas con el mismo `delivery_id`).
    - Una intervención conserva TODO su historial de entregas, incluidas las
      anuladas: el estado vigente/anulado se lee de la entrega, nunca se borra
      la fila.
    - `technical_report_id` identifica exactamente qué revisión documental usó
      esta entrega en su PDF final (a lo más una entrega por revisión).
    """

    __tablename__ = "technical_intervention_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "intervention_id", "delivery_id",
            name="uq_technical_intervention_delivery",
        ),
        UniqueConstraint(
            "technical_report_id",
            name="uq_technical_intervention_delivery_report",
        ),
        Index("ix_technical_intervention_deliveries_delivery_id", "delivery_id"),
        Index("ix_technical_intervention_deliveries_delivery_item_id", "delivery_item_id"),
    )

    intervention_id: Mapped[int] = mapped_column(
        ForeignKey(
            "technical_interventions.id",
            name="fk_technical_intervention_deliveries_intervention_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    delivery_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lab_work_order_deliveries.id",
            name="fk_technical_intervention_deliveries_delivery_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    delivery_item_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "lab_delivery_items.id",
            name="fk_technical_intervention_deliveries_delivery_item_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    technical_report_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "technical_reports.id",
            name="fk_technical_intervention_deliveries_report_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    intervention: Mapped["TechnicalIntervention"] = relationship(back_populates="delivery_links")
    delivery: Mapped["LabWorkOrderDelivery"] = relationship(foreign_keys=[delivery_id])
    technical_report: Mapped["TechnicalReport | None"] = relationship(foreign_keys=[technical_report_id])
