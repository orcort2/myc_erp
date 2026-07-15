from __future__ import annotations

import argparse
import json

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.client import Client, ClientCertificateProfile, ClientContact
from app.services.clients import get_client_delete_eligibility


def _duplicates(db):
    rows = db.execute(
        select(func.upper(Client.rfc), func.count())
        .where(Client.is_active.is_(True), Client.rfc.is_not(None))
        .group_by(func.upper(Client.rfc))
        .having(func.count() > 1)
    ).all()
    return [{"rfc": rfc, "active_clients": count} for rfc, count in rows]


def _orphaned(db):
    contacts = db.scalar(
        select(func.count()).select_from(ClientContact).outerjoin(Client).where(Client.id.is_(None))
    ) or 0
    profiles = db.scalar(
        select(func.count()).select_from(ClientCertificateProfile).outerjoin(Client).where(Client.id.is_(None))
    ) or 0
    return {"client_contacts": contacts, "client_certificate_profiles": profiles}


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico de datos MYC (sólo lectura).")
    parser.add_argument("command", choices=["doctor", "duplicates", "orphaned", "client-delete-eligibility"])
    parser.add_argument("--client-id", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.command == "duplicates":
            result = {"active_rfc_duplicates": _duplicates(db)}
        elif args.command == "orphaned":
            result = {"orphaned": _orphaned(db)}
        elif args.command == "client-delete-eligibility":
            if args.client_id is None:
                parser.error("--client-id es requerido para client-delete-eligibility")
            result = get_client_delete_eligibility(db, args.client_id).model_dump()
        else:
            result = {
                "active_clients": int(db.scalar(select(func.count()).select_from(Client).where(Client.is_active.is_(True))) or 0),
                "archived_clients": int(db.scalar(select(func.count()).select_from(Client).where(Client.is_active.is_(False))) or 0),
                "active_rfc_duplicates": _duplicates(db),
                "orphaned": _orphaned(db),
            }
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
