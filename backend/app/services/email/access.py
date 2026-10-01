"""Fail-closed access to the GLOBAL delivery history.

Neither quotations nor invoices expose a per-record authorization function
(their routers only check ``quotations.read`` / ``invoices.read``), so a
``related_entity_type -> permission`` mapping would not prove access to the
concrete ``related_entity_id``. Until EMAIL-3/EMAIL-4 expose history from the
quotation/invoice *after* that entity passes its own authorization, the global
endpoints are limited to template managers (Administrador, Desarrollador).
``email.deliveries.read`` / ``.retry`` remain the capabilities those future
contextual endpoints will require.
"""

from sqlalchemy import Select, false

from app.models.email import EmailDelivery
from app.models.user import User
from app.services.auth import user_has_permission

GLOBAL_HISTORY_PERMISSION = "email.templates.manage"


def can_read_delivery(user: User, delivery: EmailDelivery) -> bool:
    return user_has_permission(user, GLOBAL_HISTORY_PERMISSION)


def scope_deliveries(query: Select, user: User) -> Select:
    return query if user_has_permission(user, GLOBAL_HISTORY_PERMISSION) else query.where(false())
