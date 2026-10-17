"""Independent, restart-safe quotation SMTP reconciliation runner.

Run with: python -m app.services.quotation_email_reconciliation
Deploy as a separate supervised process, never inside FastAPI lifespan.
Only updates business status from *persisted* accepted SMTP deliveries;
it does not contact SMTP or retry email.
"""

from __future__ import annotations

import logging
import os
import signal
from threading import Event
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.email import EmailDelivery
from app.models.quotation import Quotation
from app.services.quotation_email import (
    ENTITY_TYPE,
    TEMPLATE_KEY,
    reconcile_quotation_email_status,
)

logger = logging.getLogger(__name__)
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_BATCH_SIZE = 100


def reconcile_batch(
    session_factory: Callable[[], Session] = SessionLocal,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[int, int]:
    """Return (reconciled, failed). Each quotation has its own transaction.

    A bounded, keyset-paginated scan prevents one failing quotation from
    blocking other records, and avoids loading all candidates in memory.
    The row lock in reconcile_quotation_email_status serializes concurrent
    runners on PostgreSQL; the second runner rechecks the current state.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    reconciled = failed = 0
    last_id = 0
    while True:
        with session_factory() as db:
            ids = list(
                db.scalars(
                    select(Quotation.id)
                    .where(
                        Quotation.id > last_id,
                        Quotation.is_active.is_(True),
                        Quotation.status == "draft",
                        select(EmailDelivery.id)
                        .where(
                            EmailDelivery.related_entity_type == ENTITY_TYPE,
                            EmailDelivery.related_entity_id == Quotation.id,
                            EmailDelivery.template_key == TEMPLATE_KEY,
                            EmailDelivery.status == "sent",
                            EmailDelivery.sent_at.is_not(None),
                        )
                        .exists(),
                    )
                    .order_by(Quotation.id.asc())
                    .limit(batch_size)
                )
            )
        if not ids:
            break
        last_id = ids[-1]
        for quotation_id in ids:
            try:
                with session_factory() as db:
                    if reconcile_quotation_email_status(db, quotation_id):
                        reconciled += 1
            except Exception:
                failed += 1
                logger.exception("Quotation SMTP reconciliation failed quotation_id=%s", quotation_id)
        if len(ids) < batch_size:
            break
    return reconciled, failed


def run_forever(
    *,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    stop: Event | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    stop = stop or Event()
    logger.info("Quotation SMTP reconciliation started interval=%s batch=%s", interval_seconds, batch_size)
    while not stop.is_set():
        try:
            changed, failed = reconcile_batch(session_factory, batch_size=batch_size)
            if changed or failed:
                logger.info("Quotation SMTP reconciliation changed=%s failed=%s", changed, failed)
        except Exception:
            logger.exception("Quotation SMTP reconciliation scan failed; retrying next cycle")
        stop.wait(interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    run_forever(
        interval_seconds=float(os.getenv("MYC_QUOTATION_RECONCILE_INTERVAL_SECONDS", "60")),
        batch_size=int(os.getenv("MYC_QUOTATION_RECONCILE_BATCH_SIZE", "100")),
        stop=stop,
    )


if __name__ == "__main__":
    main()
