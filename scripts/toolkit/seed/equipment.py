#!/usr/bin/env python

import argparse

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.schemas.equipment import EquipmentCreate
from app.services.equipment import create_equipment


def seed_equipment(service_order_id: int, count: int, prefix: str) -> None:
    with SessionLocal() as db:
        service_order = db.get(ServiceOrder, service_order_id)
        if service_order is None or service_order.is_active is False:
            raise SystemExit(f"ETS no encontrado o inactivo: {service_order_id}")

        work_orders = db.scalars(
            select(ServiceWorkOrder)
            .where(
                ServiceWorkOrder.service_order_id == service_order_id,
                ServiceWorkOrder.is_active.is_(True),
            )
            .order_by(ServiceWorkOrder.sequence.asc(), ServiceWorkOrder.id.asc())
        ).all()
        if not work_orders:
            raise SystemExit("El ETS no tiene Ordenes de Trabajo activas.")

        created = 0
        sequence = 1
        while created < count:
            target = next(
                (work_order for work_order in work_orders if work_order.available_equipment_slots > 0),
                None,
            )
            if target is None:
                raise SystemExit(f"Sin capacidad disponible. Creados: {created}")

            create_equipment(
                db,
                EquipmentCreate(
                    service_order_id=service_order_id,
                    work_order_id=target.id,
                    calibration_scope="traceable",
                    name=f"Equipo prueba {sequence:03d}",
                    brand="MYC Seed",
                    model="DEV",
                    serial_number=f"{prefix}-SER-{sequence:04d}",
                    internal_id=f"{prefix}-INT-{sequence:04d}",
                    range_or_capacity="Rango de prueba",
                    initial_condition="Equipo generado para pruebas funcionales.",
                    notes="Seed automatico del MYC Toolkit.",
                ),
            )
            created += 1
            sequence += 1

        print(f"Equipos creados: {created}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de equipos por ETS respetando capacidad por OT.")
    parser.add_argument("--service-order-id", type=int, required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--prefix", default="SEED")
    args = parser.parse_args()
    seed_equipment(args.service_order_id, args.count, args.prefix)


if __name__ == "__main__":
    main()
