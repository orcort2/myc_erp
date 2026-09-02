"""Dev-only: purga los datos LAB usados durante QA para reiniciar desde cero.

    python -m app.scripts.reset_lab_dev_data                 # dry-run (sólo cuenta)
    python -m app.scripts.reset_lab_dev_data --confirm        # borra de verdad
    python -m app.scripts.reset_lab_dev_data --confirm --keep-folio-sequences

NUNCA se ejecuta en producción (verifica settings.environment y el host de
DATABASE_URL antes de tocar nada) y NUNCA se importa desde la app en
ejecución -- es un comando manual, no un hook de arranque.

Alcance: exclusivamente el dominio LAB (clientes, OT, equipo, firmas,
FieldSheets + resultados/firmas/certificados/incertidumbre asociados,
tickets, revisiones, conversaciones de Comunicaciones ligadas a esos
tickets, y opcionalmente los contadores de folio LAB). No toca usuarios,
permisos, catálogos globales, ni ningún dato productivo/no-LAB -- cada FK
LAB->no-LAB (clients, users, linked_companies, calibration_procedures) es
RESTRICT y nunca se sigue hacia esas tablas.

Orden de borrado (ver auditoría FK completa, cierre UX 2026-09):
  1. snapshot de ids/paths (antes de borrar nada)
  2. hijos de field_sheets LAB (results, signatures, uncertainty, reference
     standards) -- sin ondelete a nivel BD, deben irse primero
  3. field_sheets LAB (lab_equipment_id IS NOT NULL) + archivos PDF en disco
  4. limpiar FKs circulares (lab_work_orders.*_ticket_id/signature_session_id,
     lab_work_order_equipment.folio_ticket_id)
  5. lab_work_order_revisions
  6. operational_tickets (sólo tipos LAB)
  7. communication_conversations ligadas a esos tickets (CASCADE arrastra
     mensajes/recibos/menciones/participantes)
  8. lab_work_order_group_requests
  9. lab_work_order_signatures, luego lab_work_order_signature_sessions
  10. lab_work_order_equipment (limpiar self-FK primero)
  11. lab_work_orders
  12. lab_clients
  13. institutional_folio_sequences (document_type LAB) -- opcional, ver
      --keep-folio-sequences
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.storage_service import resolve_storage_path


LAB_TICKET_TYPES = (
    "reopen_work_order",
    "manual_myc_folio",
    "linked_folio",
    "partial_close",
    "certificate_folio_block",
    "field_sheet_template_request",
    "field_sheet_reopen",
)


def _assert_safe_environment() -> None:
    env = settings.environment.lower()
    if env in {"production", "prod"}:
        raise SystemExit(
            f"ABORTADO: ENVIRONMENT='{settings.environment}' parece producción. "
            "Este script sólo corre en desarrollo local."
        )
    url = make_url(settings.database_url)
    host = (url.host or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit(
            f"ABORTADO: DATABASE_URL apunta a host '{url.host}', no localhost. "
            "Este script sólo corre contra una base local."
        )
    print(f"Entorno verificado: environment='{settings.environment}', db='{url.database}'@{url.host}")


@dataclass
class ResetSummary:
    counts: dict[str, int] = field(default_factory=dict)
    pdf_files_to_unlink: list[str] = field(default_factory=list)

    def add(self, table: str, count: int) -> None:
        self.counts[table] = self.counts.get(table, 0) + count

    def print_report(self, *, executed: bool) -> None:
        title = "Registros eliminados" if executed else "Registros que se eliminarían (dry-run)"
        print(f"\n{title}:")
        total = 0
        for table, count in self.counts.items():
            if count:
                print(f"  {table}: {count}")
                total += count
        print(f"  TOTAL: {total}")
        if self.pdf_files_to_unlink:
            verb = "eliminados" if executed else "que se eliminarían"
            print(f"  Archivos PDF de FieldSheet {verb}: {len(self.pdf_files_to_unlink)}")


def _scalar_count(db: Session, sql: str) -> int:
    return db.execute(text(sql)).scalar_one()


def _collect_snapshot(db: Session, summary: ResetSummary) -> dict[str, list[int]]:
    lab_field_sheet_ids = [
        row[0] for row in db.execute(text("SELECT id FROM field_sheets WHERE lab_equipment_id IS NOT NULL"))
    ]
    lab_field_sheet_pdf_paths = [
        row[0]
        for row in db.execute(
            text(
                "SELECT final_pdf_path FROM field_sheets "
                "WHERE lab_equipment_id IS NOT NULL AND final_pdf_path IS NOT NULL"
            )
        )
    ]
    summary.pdf_files_to_unlink = lab_field_sheet_pdf_paths

    lab_work_order_ids = [row[0] for row in db.execute(text("SELECT id FROM lab_work_orders"))]

    type_list = ", ".join(f"'{item}'" for item in LAB_TICKET_TYPES)
    lab_ticket_ids = [
        row[0] for row in db.execute(text(f"SELECT id FROM operational_tickets WHERE type IN ({type_list})"))
    ]

    lab_conversation_ids: list[int] = []
    if lab_ticket_ids:
        ids_list = ", ".join(str(item) for item in lab_ticket_ids)
        lab_conversation_ids = [
            row[0]
            for row in db.execute(
                text(f"SELECT id FROM communication_conversations WHERE ticket_id IN ({ids_list})")
            )
        ]

    # Chequeo defensivo (auditoría): Certificate.field_sheet_id es nullable
    # y sin ondelete -- en teoría nunca debería apuntar a una FieldSheet LAB
    # (el certificado LAB vive como string en LabWorkOrderEquipment, no como
    # fila Certificate), pero se verifica en vez de asumirlo.
    if lab_field_sheet_ids:
        ids_list = ", ".join(str(item) for item in lab_field_sheet_ids)
        stray_certificates = _scalar_count(
            db, f"SELECT COUNT(*) FROM certificates WHERE field_sheet_id IN ({ids_list})"
        )
        if stray_certificates:
            raise SystemExit(
                f"ABORTADO: {stray_certificates} certificate(s) productivo(s) referencian una "
                "FieldSheet LAB -- esto no debería pasar; revisa manualmente antes de continuar."
            )

    return {
        "field_sheet_ids": lab_field_sheet_ids,
        "work_order_ids": lab_work_order_ids,
        "ticket_ids": lab_ticket_ids,
        "conversation_ids": lab_conversation_ids,
    }


def _delete_by_ids(db: Session, summary: ResetSummary, *, table: str, column: str, ids: list[int]) -> None:
    if not ids:
        summary.add(table, 0)
        return
    ids_list = ", ".join(str(item) for item in ids)
    result = db.execute(text(f"DELETE FROM {table} WHERE {column} IN ({ids_list})"))
    summary.add(table, result.rowcount or 0)


def _run(db: Session, *, execute: bool, keep_folio_sequences: bool) -> ResetSummary:
    summary = ResetSummary()
    snapshot = _collect_snapshot(db, summary)
    field_sheet_ids = snapshot["field_sheet_ids"]
    work_order_ids = snapshot["work_order_ids"]
    ticket_ids = snapshot["ticket_ids"]
    conversation_ids = snapshot["conversation_ids"]

    # 2. Hijos de field_sheets LAB.
    _delete_by_ids(db, summary, table="field_sheet_results", column="field_sheet_id", ids=field_sheet_ids)
    _delete_by_ids(db, summary, table="field_sheet_signatures", column="field_sheet_id", ids=field_sheet_ids)
    _delete_by_ids(db, summary, table="uncertainty_calculations", column="field_sheet_id", ids=field_sheet_ids)
    _delete_by_ids(db, summary, table="field_sheet_reference_standards", column="field_sheet_id", ids=field_sheet_ids)
    # Revisiones históricas que se superseden entre sí (self-FK) -- limpiar antes de borrar.
    if field_sheet_ids:
        ids_list = ", ".join(str(item) for item in field_sheet_ids)
        db.execute(text(f"UPDATE field_sheets SET supersedes_field_sheet_id = NULL WHERE id IN ({ids_list})"))

    # 3. field_sheets LAB.
    _delete_by_ids(db, summary, table="field_sheets", column="id", ids=field_sheet_ids)

    # 4. Romper FKs circulares con operational_tickets antes de borrar tickets/OT.
    if work_order_ids:
        ids_list = ", ".join(str(item) for item in work_order_ids)
        db.execute(
            text(
                "UPDATE lab_work_orders SET partial_close_ticket_id = NULL, "
                f"reopen_ticket_id = NULL, signature_session_id = NULL WHERE id IN ({ids_list})"
            )
        )
        db.execute(
            text(f"UPDATE lab_work_order_equipment SET folio_ticket_id = NULL WHERE work_order_id IN ({ids_list})")
        )

    # 5. Revisiones (dependen de work_order + ticket, ambos todavía sin borrar).
    _delete_by_ids(db, summary, table="lab_work_order_revisions", column="work_order_id", ids=work_order_ids)

    # 6. Tickets LAB.
    _delete_by_ids(db, summary, table="operational_tickets", column="id", ids=ticket_ids)

    # 7. Conversaciones de Comunicaciones ligadas a esos tickets (CASCADE se
    # encarga de mensajes/recibos/menciones/participantes).
    _delete_by_ids(db, summary, table="communication_conversations", column="id", ids=conversation_ids)

    # 8. Solicitudes de grupo anticipado.
    _delete_by_ids(db, summary, table="lab_work_order_group_requests", column="root_work_order_id", ids=work_order_ids)

    # 9. Firmas y sesiones de firma.
    session_ids = [
        row[0]
        for row in db.execute(
            text(
                "SELECT id FROM lab_work_order_signature_sessions "
                + (f"WHERE root_work_order_id IN ({', '.join(str(i) for i in work_order_ids)})" if work_order_ids else "WHERE 1=0")
            )
        )
    ]
    _delete_by_ids(db, summary, table="lab_work_order_signatures", column="signature_session_id", ids=session_ids)
    _delete_by_ids(db, summary, table="lab_work_order_signature_sessions", column="id", ids=session_ids)

    # 10. Equipo (limpiar self-FK de LabWorkOrder primero, ver paso 11).
    _delete_by_ids(db, summary, table="lab_work_order_equipment", column="work_order_id", ids=work_order_ids)

    # 11. OT LAB -- limpiar self-referencias (root/previous) antes de borrar.
    if work_order_ids:
        ids_list = ", ".join(str(item) for item in work_order_ids)
        db.execute(
            text(
                "UPDATE lab_work_orders SET root_work_order_id = NULL, previous_work_order_id = NULL "
                f"WHERE id IN ({ids_list})"
            )
        )
    _delete_by_ids(db, summary, table="lab_work_orders", column="id", ids=work_order_ids)

    # 12. Clientes LAB (soft-deleted incluidos -- reset es un borrado real).
    result = db.execute(text("DELETE FROM lab_clients"))
    summary.counts["lab_clients"] = result.rowcount or 0

    # 13. Contadores de folio LAB (opcional).
    if keep_folio_sequences:
        summary.counts["institutional_folio_sequences (LAB)"] = 0
    else:
        result = db.execute(
            text(
                "DELETE FROM institutional_folio_sequences "
                "WHERE document_type IN ('lab_work_order', 'lab_certificate')"
            )
        )
        summary.counts["institutional_folio_sequences (LAB)"] = result.rowcount or 0

    if execute:
        db.commit()
    else:
        db.rollback()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Ejecuta el borrado (sin esto, sólo cuenta -- dry-run).")
    parser.add_argument(
        "--keep-folio-sequences", action="store_true",
        help="No reinicia los contadores de folio LAB (OT 6400-6999, MYCA/MYCT) -- los deja donde estaban.",
    )
    args = parser.parse_args()

    _assert_safe_environment()

    db = SessionLocal()
    try:
        summary = _run(db, execute=args.confirm, keep_folio_sequences=args.keep_folio_sequences)
        summary.print_report(executed=args.confirm)

        if not args.confirm:
            print("\nDry-run -- no se borró nada. Ejecuta con --confirm para borrar de verdad.")
            return

        for relative_path in summary.pdf_files_to_unlink:
            resolved = resolve_storage_path(relative_path)
            if resolved is not None and resolved.is_file():
                resolved.unlink(missing_ok=True)
        print(f"\nListo. {len(summary.pdf_files_to_unlink)} archivo(s) PDF de FieldSheet eliminados del disco.")
        print("La base ERP real y sus catálogos/usuarios/permisos no fueron tocados.")
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
