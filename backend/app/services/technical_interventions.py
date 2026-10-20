"""Autoridad técnica por intervención (SG-4J-A2).

Única fuente de verdad para:
  1. qué intervenciones de un equipo son OBLIGATORIAS y cuál es su revisión
     documental vigente;
  2. qué entregas físicas vigentes respaldan una intervención (y qué
     intervenciones respalda una entrega);
usada por la entrega, el cierre, la finalización del reporte y el paquete.

Hoy cada equipo tiene exactamente una intervención con un reporte vigente, y
este módulo reproduce exactamente ese comportamiento; la creación funcional de
varias intervenciones y de nuevas revisiones llega en etapas posteriores.

Obligatoriedad (regla explícita)
--------------------------------
Una intervención es OBLIGATORIA para el cierre de la OT si su estado operativo
es `open` o `completed`; una intervención `cancelled` nunca bloquea. Un equipo
activo de Servicio General debe tener al menos UNA intervención obligatoria:
un equipo sin ninguna sigue bloqueando ("Sin reporte técnico"), igual que antes.
Haber sido creada NO basta por sí mismo si fue cancelada, y estar completada
tampoco exime: el documento vigente debe estar completo (PDF + entrega).

Compatibilidad: `LabWorkOrderEquipment.current_technical_report` es el reporte
vigente de la intervención PRINCIPAL (no cancelada, de menor id, con revisión
vigente); este módulo es la vía para consultar TODAS las intervenciones.
Desde SG-4J-A3 `technical_reports.intervention_id` es NOT NULL: ya no existen
reportes sin intervención.

Este módulo sólo importa modelos: no hay ciclos con los servicios que lo usan.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport

MANDATORY_INTERVENTION_STATUSES = frozenset({"open", "completed"})

DeliveryRow = tuple[LabWorkOrderDelivery, LabDeliveryItem | None]


@dataclass(frozen=True)
class InterventionRef:
    """Una intervención obligatoria y su revisión documental vigente."""

    intervention: TechnicalIntervention | None
    report: TechnicalReport | None

    @property
    def intervention_id(self) -> int | None:
        return self.intervention.id if self.intervention is not None else None

    @property
    def folio(self) -> str | None:
        if self.intervention is not None:
            return self.intervention.folio
        return self.report.folio if self.report is not None else None


# ---------------------------------------------------------------------------
# 1. Intervenciones obligatorias y revisión vigente
# ---------------------------------------------------------------------------

def is_mandatory(intervention: TechnicalIntervention) -> bool:
    return intervention.status in MANDATORY_INTERVENTION_STATUSES


def current_revision(intervention: TechnicalIntervention) -> TechnicalReport | None:
    """Revisión vigente, determinista: la de mayor `revision_number` entre las
    marcadas `is_current` (a lo más una por la restricción única; el desempate
    por id cubre datos anómalos sin elegir al azar)."""
    current = [report for report in intervention.reports if report.is_current]
    if not current:
        return None
    return max(current, key=lambda report: (report.revision_number, report.id))


def equipment_interventions(equipment: LabWorkOrderEquipment) -> list[InterventionRef]:
    """Intervenciones OBLIGATORIAS del equipo, ordenadas por id (estable), cada
    una con su revisión vigente. Vacío si el equipo no tiene ninguna."""
    return [
        InterventionRef(intervention, current_revision(intervention))
        for intervention in sorted(equipment.technical_interventions, key=lambda item: item.id)
        if is_mandatory(intervention)
    ]


def equipment_report_folios(equipment: LabWorkOrderEquipment) -> list[str]:
    """Folios institucionales de TODAS las intervenciones obligatorias del
    equipo (orden estable por id); es lo que se imprime en la OT y el acuse."""
    return [ref.folio for ref in equipment_interventions(equipment) if ref.folio]


def has_single_intervention(equipment: LabWorkOrderEquipment) -> bool:
    """Con una sola intervención no cancelada el equipo identifica sin
    ambigüedad a la intervención (habilita el respaldo por equipo)."""
    return len([item for item in equipment.technical_interventions if item.status != "cancelled"]) <= 1


# ---------------------------------------------------------------------------
# 2. Entregas que respaldan una intervención
# ---------------------------------------------------------------------------

@dataclass
class DeliveryIndex:
    """Entregas VIGENTES (`completed`, nunca `voided`) cargadas en bloque:
    una consulta por vínculo y otra por equipo, sin N+1."""

    by_intervention: dict[int, list[DeliveryRow]] = field(default_factory=dict)
    by_equipment: dict[int, list[DeliveryRow]] = field(default_factory=dict)

    def for_ref(self, ref: InterventionRef, equipment: LabWorkOrderEquipment) -> list[DeliveryRow]:
        """Entregas vigentes de la intervención: por vínculo explícito; sólo si
        no existe ninguno y el equipo tiene una única intervención se usa el
        respaldo por equipo (entregas anteriores a los vínculos)."""
        if ref.intervention_id is not None and self.by_intervention.get(ref.intervention_id):
            return self.by_intervention[ref.intervention_id]
        if ref.intervention_id is None or has_single_intervention(equipment):
            return self.by_equipment.get(equipment.id, [])
        return []


def load_delivery_index(db: Session, equipments: list[LabWorkOrderEquipment]) -> DeliveryIndex:
    index = DeliveryIndex()
    equipment_ids = [equipment.id for equipment in equipments]
    intervention_ids = [
        intervention.id for equipment in equipments for intervention in equipment.technical_interventions
    ]
    if intervention_ids:
        for delivery, link, item in db.execute(
            select(LabWorkOrderDelivery, TechnicalInterventionDelivery, LabDeliveryItem)
            .join(TechnicalInterventionDelivery, TechnicalInterventionDelivery.delivery_id == LabWorkOrderDelivery.id)
            .outerjoin(LabDeliveryItem, LabDeliveryItem.id == TechnicalInterventionDelivery.delivery_item_id)
            .where(
                TechnicalInterventionDelivery.intervention_id.in_(intervention_ids),
                LabWorkOrderDelivery.status == "completed",
            )
            .order_by(LabWorkOrderDelivery.id, TechnicalInterventionDelivery.id)
        ).all():
            index.by_intervention.setdefault(link.intervention_id, []).append((delivery, item))
    if equipment_ids:
        for delivery, item in db.execute(
            select(LabWorkOrderDelivery, LabDeliveryItem)
            .join(LabDeliveryItem, LabDeliveryItem.delivery_id == LabWorkOrderDelivery.id)
            .where(LabDeliveryItem.equipment_id.in_(equipment_ids), LabWorkOrderDelivery.status == "completed")
            .order_by(LabWorkOrderDelivery.id)
        ).all():
            index.by_equipment.setdefault(item.equipment_id, []).append((delivery, item))
    return index


def current_deliveries_for_equipment(db: Session, equipment_id: int) -> list[tuple[LabWorkOrderDelivery, LabDeliveryItem]]:
    """Entregas VIGENTES que incluyen el equipo (consulta por ítem de entrega)."""
    rows = db.execute(
        select(LabWorkOrderDelivery, LabDeliveryItem)
        .join(LabDeliveryItem, LabDeliveryItem.delivery_id == LabWorkOrderDelivery.id)
        .where(LabDeliveryItem.equipment_id == equipment_id, LabWorkOrderDelivery.status == "completed")
        .order_by(LabWorkOrderDelivery.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def current_deliveries_for_intervention(
    db: Session, equipment: LabWorkOrderEquipment, ref: InterventionRef
) -> list[DeliveryRow]:
    return load_delivery_index(db, [equipment]).for_ref(ref, equipment)


def delivery_backed_interventions(db: Session, delivery_id: int) -> list[TechnicalIntervention]:
    """Intervenciones que respalda una entrega física, ordenadas por id: las
    vinculadas explícitamente y, para entregas sin vínculo, las de los equipos
    del ítem que tengan una única intervención."""
    linked = list(
        db.scalars(
            select(TechnicalIntervention)
            .join(TechnicalInterventionDelivery, TechnicalInterventionDelivery.intervention_id == TechnicalIntervention.id)
            .where(TechnicalInterventionDelivery.delivery_id == delivery_id)
        )
    )
    linked_equipment = {item.lab_equipment_id for item in linked}
    fallback = []
    for item in db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == delivery_id)):
        if item.equipment_id is None or item.equipment_id in linked_equipment:
            continue
        candidates = list(
            db.scalars(
                select(TechnicalIntervention).where(
                    TechnicalIntervention.lab_equipment_id == item.equipment_id,
                    TechnicalIntervention.status != "cancelled",
                )
            )
        )
        if len(candidates) == 1:
            fallback.append(candidates[0])
    return sorted({item.id: item for item in [*linked, *fallback]}.values(), key=lambda item: item.id)
