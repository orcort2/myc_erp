"""enable multiple technical interventions per equipment (SG-4J-A3)

Revision ID: c6d9e2f5a8b1
Revises: a4b7c1d9e3f2
Create Date: 2026-10-08

Habilitación ESTRUCTURAL (no funcional): el esquema admite varias intervenciones
por equipo, cada una con su folio, revisiones e historial de entregas. Ni la API
pública ni Mobile crean todavía varias intervenciones; no hay flujo de R2.

Restricciones heredadas de `technical_reports` -- auditoría
-----------------------------------------------------------
* `uq_technical_reports_current_lab_equipment` (UNIQUE lab_equipment_id WHERE
  is_current): RETIRADA. Expresaba "un vigente por equipo"; la vigencia es ahora
  POR INTERVENCIÓN (`uq_technical_reports_current_intervention`, creada en A1).
* `uq_technical_reports_folio` (UNIQUE folio): RETIRADA. El folio institucional
  pertenece a la intervención (`technical_interventions.folio`, único) y R1/R2 de
  una misma intervención deben compartirlo. `folio` queda indexado (no único).
* `uq_technical_reports_supersedes_report_id`: CONSERVADA. Una revisión sólo
  puede ser sucedida por otra (sin bifurcaciones); sigue siendo correcta dentro
  de una intervención.
* `uq_technical_reports_intervention_revision` y
  `uq_technical_reports_current_intervention` (A1): CONSERVADAS (trasladan a la
  intervención la unicidad de revisión y de vigencia).

Nuevo en esta migración
-----------------------
* `technical_reports.intervention_id` pasa a NOT NULL (tras verificar que todo
  reporte tiene intervención válida).
* FK compuesta `(intervention_id, lab_equipment_id) -> technical_interventions
  (id, lab_equipment_id)`: un reporte pertenece al MISMO equipo que su
  intervención.
* FK compuesta `(supersedes_report_id, intervention_id) -> technical_reports
  (id, intervention_id)`: una revisión sólo supersede a otra de la MISMA
  intervención.

No altera PDFs, firmas, snapshots, hashes, folios ni auditoría; no genera folios.

Downgrade: restaura las restricciones heredadas SOLO si los datos todavía las
cumplen (sin folios compartidos entre revisiones ni equipos con varios reportes
vigentes); si no, ABORTA con un mensaje claro en lugar de perder documentos.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c6d9e2f5a8b1"
down_revision: Union[str, None] = "a4b7c1d9e3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class UnsafeTechnicalReportConstraintChange(RuntimeError):
    """Los datos no permiten aplicar/revertir el cambio de forma segura."""


def _count(connection, sql: str) -> int:
    return connection.execute(sa.text(sql)).scalar() or 0


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Verificación previa: nada se corrige en silencio.
    if _count(connection, "SELECT count(*) FROM technical_reports WHERE intervention_id IS NULL"):
        raise UnsafeTechnicalReportConstraintChange(
            "Hay reportes técnicos sin intervención: ejecuta/revisa el backfill de SG-4J-A1 antes de continuar"
        )
    if _count(connection, (
        "SELECT count(*) FROM technical_reports r "
        "LEFT JOIN technical_interventions i ON i.id = r.intervention_id WHERE i.id IS NULL"
    )):
        raise UnsafeTechnicalReportConstraintChange("Hay reportes con una intervención inexistente")
    if _count(connection, (
        "SELECT count(*) FROM technical_reports r "
        "JOIN technical_interventions i ON i.id = r.intervention_id WHERE i.lab_equipment_id <> r.lab_equipment_id"
    )):
        raise UnsafeTechnicalReportConstraintChange("Hay reportes cuyo equipo no coincide con el de su intervención")
    if _count(connection, (
        "SELECT count(*) FROM technical_reports r JOIN technical_reports p ON p.id = r.supersedes_report_id "
        "WHERE p.intervention_id <> r.intervention_id"
    )):
        raise UnsafeTechnicalReportConstraintChange("Hay revisiones que supersede a un reporte de otra intervención")

    # 2. Destinos de las FK compuestas.
    op.create_unique_constraint(
        "uq_technical_interventions_id_equipment", "technical_interventions", ["id", "lab_equipment_id"],
    )
    op.create_unique_constraint(
        "uq_technical_reports_id_intervention", "technical_reports", ["id", "intervention_id"],
    )

    # 3. NOT NULL + integridad compuesta.
    op.alter_column("technical_reports", "intervention_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "fk_technical_reports_intervention_equipment", "technical_reports", "technical_interventions",
        ["intervention_id", "lab_equipment_id"], ["id", "lab_equipment_id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_reports_supersedes_same_intervention", "technical_reports", "technical_reports",
        ["supersedes_report_id", "intervention_id"], ["id", "intervention_id"], ondelete="RESTRICT",
    )

    # 4. Retiro de las restricciones heredadas incompatibles con varias
    #    intervenciones / folio compartido por revisiones.
    op.drop_index("uq_technical_reports_current_lab_equipment", table_name="technical_reports")
    op.drop_constraint("uq_technical_reports_folio", "technical_reports", type_="unique")
    op.create_index("ix_technical_reports_folio", "technical_reports", ["folio"])


def downgrade() -> None:
    connection = op.get_bind()
    if _count(connection, (
        "SELECT count(*) FROM (SELECT folio FROM technical_reports GROUP BY folio HAVING count(*) > 1) shared"
    )):
        raise UnsafeTechnicalReportConstraintChange(
            "No se puede restaurar la unicidad de folio por reporte: hay revisiones que comparten folio"
        )
    if _count(connection, (
        "SELECT count(*) FROM (SELECT lab_equipment_id FROM technical_reports WHERE is_current "
        "GROUP BY lab_equipment_id HAVING count(*) > 1) many"
    )):
        raise UnsafeTechnicalReportConstraintChange(
            "No se puede restaurar 'un reporte vigente por equipo': hay equipos con varias intervenciones vigentes"
        )

    op.drop_index("ix_technical_reports_folio", table_name="technical_reports")
    op.create_unique_constraint("uq_technical_reports_folio", "technical_reports", ["folio"])
    op.create_index(
        "uq_technical_reports_current_lab_equipment", "technical_reports", ["lab_equipment_id"],
        unique=True, postgresql_where=sa.text("is_current IS TRUE"),
    )
    op.drop_constraint("fk_technical_reports_supersedes_same_intervention", "technical_reports", type_="foreignkey")
    op.drop_constraint("fk_technical_reports_intervention_equipment", "technical_reports", type_="foreignkey")
    op.alter_column("technical_reports", "intervention_id", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("uq_technical_reports_id_intervention", "technical_reports", type_="unique")
    op.drop_constraint("uq_technical_interventions_id_equipment", "technical_interventions", type_="unique")
