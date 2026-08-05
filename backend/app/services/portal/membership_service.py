from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.portal.constants import ClientPortalMembershipStatus, PortalAccountType
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.models.client_link_request import ClientLinkRequest
from app.models.portal_registration import PortalRegistration
from app.models.notification import Notification
from app.core.portal.constants import ClientLinkRequestStatus, PortalRegistrationStatus


def _load(db: Session, membership_id: int) -> ClientPortalMembership:
    item = db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.id == membership_id).options(*_membership_options()))
    if item is None:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")
    return item


def _roles(db: Session, client_id: int, codes: list[str]) -> list[ClientPortalRole]:
    roles = list(db.scalars(select(ClientPortalRole).where(ClientPortalRole.code.in_(codes), ClientPortalRole.is_active.is_(True), (ClientPortalRole.client_id.is_(None)) | (ClientPortalRole.client_id == client_id))).all())
    if {role.code for role in roles} != set(codes):
        raise HTTPException(status_code=422, detail="Uno o más roles no son asignables")
    return roles


def serialize(item: ClientPortalMembership) -> dict:
    permissions = sorted(
        {
            permission.permission.code
            for link in item.membership_roles
            for permission in link.role.role_permissions
            if permission.permission.is_active
        }
    )
    source = "administrative"
    if item.source_link_request is not None:
        source = "public_registration"
    elif item.source_invitation is not None:
        source = "invitation"
    return {"id": item.id, "client_id": item.client_id, "client_name": item.client.commercial_name or item.client.legal_name, "client_legal_name": item.client.legal_name, "client_commercial_name": item.client.commercial_name, "user_id": item.user_id, "username": item.user.username, "email": item.user.email, "full_name": item.user.full_name, "account_status": item.user.status, "account_is_active": item.user.is_active, "email_verified_at": item.user.email_verified_at, "last_login_at": item.user.last_login_at, "password_changed_at": item.user.password_changed_at, "must_change_password": item.user.must_change_password, "failed_login_attempts": item.user.failed_login_attempts, "locked_until": item.user.locked_until, "status": item.status, "is_primary_contact": item.is_primary_contact, "role_codes": [link.role.code for link in item.membership_roles], "created_at": item.created_at, "approved_at": item.approved_at, "approved_by": item.approved_by, "approved_by_name": item.approved_by_user.full_name if item.approved_by_user else None, "source": source, "effective_permissions": permissions}


def _membership_options():
    return (
        selectinload(ClientPortalMembership.user),
        selectinload(ClientPortalMembership.client),
        selectinload(ClientPortalMembership.approved_by_user),
        selectinload(ClientPortalMembership.membership_roles)
        .selectinload(ClientPortalMembershipRole.role)
        .selectinload(ClientPortalRole.role_permissions)
        .selectinload(ClientPortalRolePermission.permission),
        selectinload(ClientPortalMembership.source_link_request),
        selectinload(ClientPortalMembership.source_invitation),
    )


def list_memberships(db: Session, client_id: int | None = None) -> list[dict]:
    query = select(ClientPortalMembership).options(*_membership_options()).order_by(ClientPortalMembership.created_at.desc())
    if client_id is not None:
        query = query.where(ClientPortalMembership.client_id == client_id)
    return [serialize(item) for item in db.scalars(query).all()]


def create_membership(db: Session, *, client_id: int, user_id: int, role_codes: list[str], primary: bool, actor_id: int) -> dict:
    client, user = db.get(Client, client_id), db.get(User, user_id)
    if client is None or user is None or user.account_type != PortalAccountType.CLIENT_PORTAL.value:
        raise HTTPException(status_code=404, detail="Cliente o cuenta del portal no encontrados")
    if db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.client_id == client_id, ClientPortalMembership.user_id == user_id)):
        raise HTTPException(status_code=409, detail="La membresía ya existe")
    roles = _roles(db, client_id, role_codes)
    item = ClientPortalMembership(client_id=client_id, user_id=user_id, status=ClientPortalMembershipStatus.ACTIVE.value, is_primary_contact=primary, approved_by=actor_id, approved_at=datetime.now(timezone.utc))
    db.add(item); db.flush()
    for role in roles:
        db.add(ClientPortalMembershipRole(membership_id=item.id, role_id=role.id))
    write_audit_log(db, action="portal.membership.created", entity="client_portal_memberships", entity_id=item.id, user_id=actor_id, new_values={"client_id": client_id, "user_id": user_id, "role_codes": role_codes})
    db.commit()
    return serialize(_load(db, item.id))


def _active_admin_count(db: Session, client_id: int) -> int:
    return db.scalar(select(func.count(func.distinct(ClientPortalMembership.id))).join(ClientPortalMembershipRole).join(ClientPortalRole).where(ClientPortalMembership.client_id == client_id, ClientPortalMembership.status == ClientPortalMembershipStatus.ACTIVE.value, ClientPortalRole.code == "portal_administrator")) or 0


def _protect_last_admin(db: Session, item: ClientPortalMembership, new_codes: list[str] | None = None) -> None:
    current = {link.role.code for link in item.membership_roles}
    removing = "portal_administrator" in current and (new_codes is None or "portal_administrator" not in new_codes)
    if removing and item.status == ClientPortalMembershipStatus.ACTIVE.value and _active_admin_count(db, item.client_id) <= 1:
        raise HTTPException(status_code=409, detail="No se puede retirar al último administrador activo del cliente")


def update_status(db: Session, membership_id: int, status_value: str, actor_id: int, reason: str) -> dict:
    item = _load(db, membership_id)
    if status_value in {ClientPortalMembershipStatus.SUSPENDED.value, ClientPortalMembershipStatus.REVOKED.value}:
        _protect_last_admin(db, item)
    now = datetime.now(timezone.utc)
    item.status = status_value
    if status_value == ClientPortalMembershipStatus.SUSPENDED.value:
        item.suspended_by, item.suspended_at, item.suspension_reason = actor_id, now, reason
    elif status_value == ClientPortalMembershipStatus.REVOKED.value:
        item.revoked_by, item.revoked_at, item.revocation_reason = actor_id, now, reason
    elif status_value == ClientPortalMembershipStatus.ACTIVE.value:
        item.suspended_by = item.suspended_at = item.suspension_reason = None
    write_audit_log(db, action=f"portal.membership.{status_value}", entity="client_portal_memberships", entity_id=item.id, user_id=actor_id, new_values={"status": status_value, "reason": reason})
    db.commit()
    return serialize(_load(db, item.id))


def replace_roles(db: Session, membership_id: int, role_codes: list[str], actor_id: int) -> dict:
    item = _load(db, membership_id)
    _protect_last_admin(db, item, role_codes)
    roles = _roles(db, item.client_id, role_codes)
    for link in list(item.membership_roles):
        db.delete(link)
    db.flush()
    for role in roles:
        db.add(ClientPortalMembershipRole(membership_id=item.id, role_id=role.id))
    write_audit_log(db, action="portal.membership.roles_updated", entity="client_portal_memberships", entity_id=item.id, user_id=actor_id, new_values={"role_codes": role_codes})
    db.commit()
    return serialize(_load(db, item.id))


def set_primary(db: Session, membership_id: int, actor_id: int) -> dict:
    item = _load(db, membership_id)
    for membership in db.scalars(select(ClientPortalMembership).where(ClientPortalMembership.client_id == item.client_id)).all():
        membership.is_primary_contact = membership.id == item.id
    write_audit_log(db, action="portal.membership.primary_changed", entity="client_portal_memberships", entity_id=item.id, user_id=actor_id)
    db.commit()
    return serialize(_load(db, item.id))


def serialize_link(item: ClientLinkRequest) -> dict:
    registration = item.portal_registration
    return {"id": item.id, "portal_registration_id": item.portal_registration_id, "proposed_client_id": item.proposed_client_id, "status": item.status, "request_reason": item.request_reason, "resolution_reason": item.resolution_reason, "resulting_membership_id": item.resulting_membership_id, "created_at": item.created_at, "updated_at": item.updated_at, "registration_user_id": registration.user_id, "registration_username": registration.user.username, "registration_email": registration.user.email, "registration_full_name": registration.user.full_name, "declared_company_name": registration.declared_company_name, "declared_company_rfc": registration.declared_company_rfc, "proposed_client_name": item.proposed_client.commercial_name or item.proposed_client.legal_name, "requested_by": item.requested_by, "requested_by_name": item.requested_by_user.full_name, "reviewed_by": item.reviewed_by, "reviewed_by_name": item.reviewed_by_user.full_name if item.reviewed_by_user else None, "reviewed_at": item.reviewed_at, "resolved_by": item.resolved_by, "resolved_by_name": item.resolved_by_user.full_name if item.resolved_by_user else None, "resolved_at": item.resolved_at}


def list_registrations(db: Session) -> list[PortalRegistration]:
    return list(db.scalars(select(PortalRegistration).options(selectinload(PortalRegistration.user)).order_by(PortalRegistration.created_at.desc())).all())


def list_link_requests(db: Session) -> list[dict]:
    query = select(ClientLinkRequest).options(
        selectinload(ClientLinkRequest.portal_registration).selectinload(PortalRegistration.user),
        selectinload(ClientLinkRequest.proposed_client),
        selectinload(ClientLinkRequest.requested_by_user),
        selectinload(ClientLinkRequest.reviewed_by_user),
        selectinload(ClientLinkRequest.resolved_by_user),
    ).order_by(ClientLinkRequest.created_at.desc())
    return [serialize_link(item) for item in db.scalars(query).all()]


def take_link_request_for_review(db: Session, request_id: int, actor_id: int) -> dict:
    item = db.get(ClientLinkRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if item.status != ClientLinkRequestStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="La solicitud no está pendiente")
    item.status = ClientLinkRequestStatus.UNDER_REVIEW.value
    item.reviewed_by = actor_id
    item.reviewed_at = datetime.now(timezone.utc)
    write_audit_log(db, action="portal.link_request.review_started", entity="client_link_requests", entity_id=item.id, user_id=actor_id)
    db.commit()
    return next(row for row in list_link_requests(db) if row["id"] == item.id)


def cancel_link_request(db: Session, request_id: int, reason: str | None, actor_id: int) -> dict:
    item = db.get(ClientLinkRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if item.status not in {ClientLinkRequestStatus.PENDING.value, ClientLinkRequestStatus.UNDER_REVIEW.value}:
        raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta")
    item.status = ClientLinkRequestStatus.CANCELLED.value
    item.resolved_by = actor_id
    item.resolved_at = datetime.now(timezone.utc)
    item.resolution_reason = reason
    write_audit_log(db, action="portal.link_request.cancelled", entity="client_link_requests", entity_id=item.id, user_id=actor_id, new_values={"reason": reason})
    db.commit()
    return next(row for row in list_link_requests(db) if row["id"] == item.id)


def create_link_request(db: Session, registration_id: int, client_id: int, reason: str | None, actor_id: int) -> dict:
    registration, client = db.get(PortalRegistration, registration_id), db.get(Client, client_id)
    if registration is None or client is None:
        raise HTTPException(status_code=404, detail="Registro o cliente no encontrado")
    if registration.email_verified_at is None or registration.status not in {PortalRegistrationStatus.PENDING_REVIEW.value, PortalRegistrationStatus.LINK_REQUESTED.value}:
        raise HTTPException(status_code=409, detail="El registro no está listo para vinculación")
    if db.scalar(select(ClientLinkRequest).where(ClientLinkRequest.portal_registration_id == registration_id, ClientLinkRequest.proposed_client_id == client_id)):
        raise HTTPException(status_code=409, detail="La solicitud de vínculo ya existe")
    item = ClientLinkRequest(portal_registration_id=registration_id, proposed_client_id=client_id, requested_by=actor_id, status=ClientLinkRequestStatus.PENDING.value, request_reason=reason)
    db.add(item); db.flush()
    registration.status = PortalRegistrationStatus.LINK_REQUESTED.value
    write_audit_log(db, action="portal.link_request.created", entity="client_link_requests", entity_id=item.id, user_id=actor_id, new_values={"registration_id": registration_id, "client_id": client_id})
    db.commit()
    return serialize_link(item)


def resolve_link_request(db: Session, request_id: int, *, approve: bool, reason: str, role_codes: list[str], actor_id: int) -> dict:
    item = db.get(ClientLinkRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if item.status not in {ClientLinkRequestStatus.PENDING.value, ClientLinkRequestStatus.UNDER_REVIEW.value}:
        raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta")
    registration = db.get(PortalRegistration, item.portal_registration_id)
    now = datetime.now(timezone.utc)
    item.reviewed_by = item.resolved_by = actor_id
    item.reviewed_at = item.resolved_at = now
    item.resolution_reason = reason
    if approve:
        if db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.client_id == item.proposed_client_id, ClientPortalMembership.user_id == registration.user_id)):
            raise HTTPException(status_code=409, detail="La cuenta ya está vinculada")
        roles = _roles(db, item.proposed_client_id, role_codes)
        membership = ClientPortalMembership(client_id=item.proposed_client_id, user_id=registration.user_id, status=ClientPortalMembershipStatus.ACTIVE.value, approved_by=actor_id, approved_at=now)
        db.add(membership); db.flush()
        for role in roles:
            db.add(ClientPortalMembershipRole(membership_id=membership.id, role_id=role.id))
        item.status = ClientLinkRequestStatus.APPROVED.value
        item.resulting_membership_id = membership.id
        registration.status = PortalRegistrationStatus.LINKED.value
    else:
        item.status = ClientLinkRequestStatus.REJECTED.value
        registration.status = PortalRegistrationStatus.REJECTED.value
    notification_recipients = {registration.user_id, item.requested_by} - {actor_id}
    for recipient_id in notification_recipients:
        db.add(
            Notification(
                recipient_user_id=recipient_id,
                actor_user_id=actor_id,
                notification_type="portal_link_resolved",
                title=(
                    "Vinculación del portal aprobada"
                    if approve
                    else "Vinculación del portal rechazada"
                ),
                body=reason,
                entity_type="client_link_request",
                entity_id=item.id,
                activity_message_id=None,
                priority="normal",
                metadata_json={
                    "status": item.status,
                    "registration_id": registration.id,
                    "membership_id": item.resulting_membership_id,
                },
            )
        )
    write_audit_log(db, action="portal.link_request.approved" if approve else "portal.link_request.rejected", entity="client_link_requests", entity_id=item.id, user_id=actor_id, new_values={"reason": reason, "membership_id": item.resulting_membership_id})
    db.commit()
    return serialize_link(item)
