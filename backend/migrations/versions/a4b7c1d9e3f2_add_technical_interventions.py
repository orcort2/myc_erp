"""add technical interventions (SG-4J-A1)

Revision ID: a4b7c1d9e3f2
Revises: ef09a7ea9e97
Create Date: 2026-10-08

Etapa ADITIVA del modelo TechnicalIntervention:

* Crea `technical_interventions` (identidad estable de un trabajo técnico) y
  `technical_intervention_deliveries` (intervención <-> entrega física).
* Agrega `technical_reports.intervention_id` (nullable) y las restricciones
  futuras `(intervention_id, revision_number)` único y una sola revisión
  vigente por intervención.
* NO retira ninguna restricción heredada (folio único, un vigente por equipo,
  supersedes único): siguen protegiendo el flujo de Instalación hasta que sus
  consumidores migren (SG-4J-A2).
* Backfill DETERMINISTA: una intervención por cadena documental existente
  (reconstruida con supersedes_report_id). Cadenas corruptas (ciclos, forks,
  referencias huérfanas, equipos/tipos mezclados, revisiones no consecutivas)
  ABORTAN la migración; nunca se corrigen en silencio.
* No toca PDFs, firmas, folios, snapshots, evidencias ni auditoría existentes.

Idempotencia operacional: el backfill sólo procesa reportes con
`intervention_id IS NULL` y reutiliza una intervención ya existente con el mismo
folio, así que puede reanudarse si una ejecución anterior se interrumpió fuera
de una transacción DDL.

Downgrade: elimina SOLO las estructuras nuevas (tabla de asociación, columna,
restricciones e intervenciones). Los documentos (reportes, PDFs, evidencias,
entregas) permanecen intactos; se pierde únicamente el agrupamiento por
intervención y el vínculo entrega<->reporte, que el upgrade reconstruye.
"""

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a4b7c1d9e3f2"
down_revision: Union[str, None] = "ef09a7ea9e97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class InconsistentTechnicalReportChain(RuntimeError):
    """Cadena documental histórica inconsistente: la migración se detiene."""


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------

def upgrade() -> None:
    op.create_table(
        "technical_interventions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lab_equipment_id", sa.Integer(), nullable=False),
        sa.Column("intervention_type", sa.String(length=40), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "intervention_type IN ('installation', 'verification', 'repair', 'maintenance', 'sale')",
            name="ck_technical_intervention_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'completed', 'cancelled')",
            name="ck_technical_intervention_status",
        ),
        sa.ForeignKeyConstraint(
            ["lab_equipment_id"], ["lab_work_order_equipment.id"],
            name="fk_technical_interventions_lab_equipment_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_technical_interventions_created_by_user_id", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio", name="uq_technical_interventions_folio"),
    )
    op.create_index("ix_technical_interventions_lab_equipment_id", "technical_interventions", ["lab_equipment_id"])
    op.create_index("ix_technical_interventions_intervention_type", "technical_interventions", ["intervention_type"])
    op.create_index("ix_technical_interventions_status", "technical_interventions", ["status"])
    op.create_index("ix_technical_interventions_created_by_user_id", "technical_interventions", ["created_by_user_id"])

    op.add_column("technical_reports", sa.Column("intervention_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_technical_reports_intervention_id", "technical_reports", "technical_interventions",
        ["intervention_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_technical_reports_intervention_id", "technical_reports", ["intervention_id"])

    op.create_table(
        "technical_intervention_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intervention_id", sa.Integer(), nullable=False),
        sa.Column("delivery_id", sa.Integer(), nullable=False),
        sa.Column("delivery_item_id", sa.Integer(), nullable=True),
        sa.Column("technical_report_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["intervention_id"], ["technical_interventions.id"],
            name="fk_technical_intervention_deliveries_intervention_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"], ["lab_work_order_deliveries.id"],
            name="fk_technical_intervention_deliveries_delivery_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_item_id"], ["lab_delivery_items.id"],
            name="fk_technical_intervention_deliveries_delivery_item_id", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["technical_report_id"], ["technical_reports.id"],
            name="fk_technical_intervention_deliveries_report_id", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervention_id", "delivery_id", name="uq_technical_intervention_delivery"),
        sa.UniqueConstraint("technical_report_id", name="uq_technical_intervention_delivery_report"),
    )
    op.create_index("ix_technical_intervention_deliveries_intervention_id", "technical_intervention_deliveries", ["intervention_id"])
    op.create_index("ix_technical_intervention_deliveries_delivery_id", "technical_intervention_deliveries", ["delivery_id"])
    op.create_index("ix_technical_intervention_deliveries_delivery_item_id", "technical_intervention_deliveries", ["delivery_item_id"])

    connection = op.get_bind()
    backfill(connection)

    # Unicidad futura. Se crea DESPUÉS del backfill: hasta entonces todos los
    # intervention_id son NULL y no habría nada que validar.
    op.create_unique_constraint(
        "uq_technical_reports_intervention_revision", "technical_reports", ["intervention_id", "revision_number"],
    )
    op.create_index(
        "uq_technical_reports_current_intervention", "technical_reports", ["intervention_id"],
        unique=True, postgresql_where=sa.text("is_current IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_technical_reports_current_intervention", table_name="technical_reports")
    op.drop_constraint("uq_technical_reports_intervention_revision", "technical_reports", type_="unique")
    op.drop_table("technical_intervention_deliveries")
    op.drop_index("ix_technical_reports_intervention_id", table_name="technical_reports")
    op.drop_constraint("fk_technical_reports_intervention_id", "technical_reports", type_="foreignkey")
    op.drop_column("technical_reports", "intervention_id")
    op.drop_table("technical_interventions")


# ---------------------------------------------------------------------------
# Backfill (función pública para poder probarla sin Alembic)
# ---------------------------------------------------------------------------

_reports = sa.table(
    "technical_reports",
    sa.column("id", sa.Integer),
    sa.column("lab_equipment_id", sa.Integer),
    sa.column("report_type", sa.String),
    sa.column("folio", sa.String),
    sa.column("status", sa.String),
    sa.column("revision_number", sa.Integer),
    sa.column("is_current", sa.Boolean),
    sa.column("supersedes_report_id", sa.Integer),
    sa.column("intervention_id", sa.Integer),
    sa.column("document_snapshot", sa.JSON),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
_interventions = sa.table(
    "technical_interventions",
    sa.column("id", sa.Integer),
    sa.column("lab_equipment_id", sa.Integer),
    sa.column("intervention_type", sa.String),
    sa.column("folio", sa.String),
    sa.column("status", sa.String),
    sa.column("created_by_user_id", sa.Integer),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
_links = sa.table(
    "technical_intervention_deliveries",
    sa.column("id", sa.Integer),
    sa.column("intervention_id", sa.Integer),
    sa.column("delivery_id", sa.Integer),
    sa.column("delivery_item_id", sa.Integer),
    sa.column("technical_report_id", sa.Integer),
)
_delivery_items = sa.table(
    "lab_delivery_items",
    sa.column("id", sa.Integer),
    sa.column("delivery_id", sa.Integer),
    sa.column("equipment_id", sa.Integer),
)
_audit = sa.table(
    "audit_logs",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("action", sa.String),
    sa.column("entity", sa.String),
    sa.column("entity_id", sa.Integer),
)


def build_chains(rows: list) -> list[list]:
    """Reconstruye las cadenas documentales (R1 -> R2 -> ...) con
    `supersedes_report_id`. Lanza InconsistentTechnicalReportChain ante
    cualquier irregularidad; no corrige nada."""
    by_id = {row.id: row for row in rows}
    children: dict[int, list[int]] = defaultdict(list)
    for row in rows:
        target = row.supersedes_report_id
        if target is None:
            continue
        if target == row.id:
            raise InconsistentTechnicalReportChain(f"El reporte {row.id} se supersede a sí mismo")
        if target not in by_id:
            raise InconsistentTechnicalReportChain(f"El reporte {row.id} supersede a {target}, que no existe")
        children[target].append(row.id)
    for parent, kids in children.items():
        if len(kids) > 1:
            raise InconsistentTechnicalReportChain(f"El reporte {parent} tiene varias revisiones sucesoras: {sorted(kids)}")

    chains: list[list] = []
    visited: set[int] = set()
    for root in sorted((row for row in rows if row.supersedes_report_id is None), key=lambda row: row.id):
        chain = [root]
        visited.add(root.id)
        while children.get(chain[-1].id):
            following = by_id[children[chain[-1].id][0]]
            if following.id in visited:
                raise InconsistentTechnicalReportChain(f"Ciclo documental en el reporte {following.id}")
            chain.append(following)
            visited.add(following.id)
        chains.append(chain)
    orphaned = sorted(set(by_id) - visited)
    if orphaned:
        raise InconsistentTechnicalReportChain(f"Reportes en un ciclo sin raíz: {orphaned}")

    for chain in chains:
        _validate_chain(chain)
    return chains


def _validate_chain(chain: list) -> None:
    root = chain[0]
    for previous, current in zip(chain, chain[1:]):
        if current.lab_equipment_id != root.lab_equipment_id:
            raise InconsistentTechnicalReportChain(f"La cadena de {root.id} mezcla equipos (reporte {current.id})")
        if current.report_type != root.report_type:
            raise InconsistentTechnicalReportChain(f"La cadena de {root.id} mezcla tipos de reporte (reporte {current.id})")
        if current.revision_number != previous.revision_number + 1:
            raise InconsistentTechnicalReportChain(
                f"Revisiones no consecutivas en la cadena de {root.id}: {previous.revision_number} -> {current.revision_number}"
            )
    current_reports = [report.id for report in chain if report.is_current]
    if len(current_reports) > 1:
        raise InconsistentTechnicalReportChain(f"La cadena de {root.id} tiene varias revisiones vigentes: {current_reports}")
    if current_reports and current_reports[0] != chain[-1].id:
        raise InconsistentTechnicalReportChain(f"La revisión vigente de la cadena de {root.id} no es la última")


def _operational_status(tip) -> str:
    if tip.status == "completed":
        return "completed"
    if tip.status == "cancelled":
        return "cancelled"
    return "open"


def backfill(connection) -> dict[str, int]:
    """Una intervención por cadena existente + vínculos con sus entregas."""
    rows = connection.execute(
        sa.select(
            _reports.c.id, _reports.c.lab_equipment_id, _reports.c.report_type, _reports.c.folio,
            _reports.c.status, _reports.c.revision_number, _reports.c.is_current,
            _reports.c.supersedes_report_id, _reports.c.intervention_id, _reports.c.document_snapshot,
            _reports.c.created_at,
        ).order_by(_reports.c.id)
    ).all()
    chains = build_chains(rows)

    created = 0
    for chain in chains:
        root, tip = chain[0], chain[-1]
        existing = connection.execute(
            sa.select(_interventions.c.id).where(_interventions.c.folio == root.folio)
        ).scalar()
        if existing is None:
            actor = connection.execute(
                sa.select(_audit.c.user_id)
                .where(
                    _audit.c.action == "technical_report.created",
                    _audit.c.entity == "technical_reports",
                    _audit.c.entity_id == root.id,
                )
                .order_by(_audit.c.id)
                .limit(1)
            ).scalar()
            existing = _insert_returning_id(connection, root, tip, actor)
            created += 1
        connection.execute(
            sa.update(_reports)
            .where(_reports.c.id.in_([report.id for report in chain]), _reports.c.intervention_id.is_(None))
            .values(intervention_id=existing)
        )

    links = _backfill_delivery_links(connection, chains)
    _verify(connection, chains)
    return {"interventions": created, "reports": len(rows), "delivery_links": links}


def _insert_returning_id(connection, root, tip, actor) -> int:
    return connection.execute(
        sa.insert(_interventions).values(
            lab_equipment_id=root.lab_equipment_id, intervention_type=root.report_type, folio=root.folio,
            status=_operational_status(tip), created_by_user_id=actor, created_at=root.created_at,
            updated_at=root.created_at,
        ).returning(_interventions.c.id)
    ).scalar_one()


def _backfill_delivery_links(connection, chains: list[list]) -> int:
    """Vincula cada intervención con TODAS las entregas (también anuladas) que
    incluyen su equipo y marca qué revisión usó cada una según el snapshot."""
    created = 0
    for chain in chains:
        root = chain[0]
        intervention_id = connection.execute(
            sa.select(_interventions.c.id).where(_interventions.c.folio == root.folio)
        ).scalar()
        used_by_delivery = {}
        for report in chain:
            snapshot = report.document_snapshot
            if isinstance(snapshot, str):
                import json

                snapshot = json.loads(snapshot)
            delivery_id = ((snapshot or {}).get("delivery") or {}).get("delivery_id")
            if delivery_id is not None:
                used_by_delivery[delivery_id] = report.id
        items = connection.execute(
            sa.select(_delivery_items.c.id, _delivery_items.c.delivery_id)
            .where(_delivery_items.c.equipment_id == root.lab_equipment_id)
            .order_by(_delivery_items.c.delivery_id, _delivery_items.c.id)
        ).all()
        for item in items:
            already = connection.execute(
                sa.select(_links.c.id).where(
                    _links.c.intervention_id == intervention_id, _links.c.delivery_id == item.delivery_id,
                )
            ).scalar()
            if already is not None:
                continue
            connection.execute(
                sa.insert(_links).values(
                    intervention_id=intervention_id, delivery_id=item.delivery_id, delivery_item_id=item.id,
                    technical_report_id=used_by_delivery.get(item.delivery_id),
                )
            )
            created += 1
    return created


def _verify(connection, chains: list[list]) -> None:
    missing = connection.execute(
        sa.select(sa.func.count()).select_from(_reports).where(_reports.c.intervention_id.is_(None))
    ).scalar()
    if missing:
        raise InconsistentTechnicalReportChain(f"{missing} reportes quedaron sin intervención")
    interventions = connection.execute(sa.select(sa.func.count()).select_from(_interventions)).scalar()
    if interventions < len(chains):
        raise InconsistentTechnicalReportChain("Hay menos intervenciones que cadenas documentales")
    for chain in chains:
        folio = chain[0].folio
        count = connection.execute(
            sa.select(sa.func.count()).select_from(_reports).join(
                _interventions, _reports.c.intervention_id == _interventions.c.id
            ).where(_interventions.c.folio == folio)
        ).scalar()
        if count != len(chain):
            raise InconsistentTechnicalReportChain(f"La intervención {folio} no agrupa su cadena completa")
