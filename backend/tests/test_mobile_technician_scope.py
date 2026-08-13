from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import create_access_token
from app.main import app
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.user import Role, User


@pytest.fixture()
def mobile_technician_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db:
        technician_role = Role(name="Tecnico", description="Técnico")
        capture_role = Role(name="Captura", description="Captura")
        assigned_only_role = Role(
            name="MobileAssignedOnly",
            description="Fixture sin permiso de hojas",
        )
        db.add_all([technician_role, capture_role, assigned_only_role])
        db.flush()

        technician_a = User(
            username="mobile-tech-a",
            email="mobile-tech-a@example.test",
            full_name="Técnico A",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            email_verified_at=datetime.now(timezone.utc),
            role_id=technician_role.id,
            roles=[technician_role],
        )
        technician_b = User(
            username="mobile-tech-b",
            email="mobile-tech-b@example.test",
            full_name="Técnico B",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            email_verified_at=datetime.now(timezone.utc),
            role_id=technician_role.id,
            roles=[technician_role],
        )
        unauthorized_user = User(
            username="mobile-capture",
            email="mobile-capture@example.test",
            full_name="Usuario Captura",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            email_verified_at=datetime.now(timezone.utc),
            role_id=capture_role.id,
            roles=[capture_role],
        )
        assigned_only_user = User(
            username="mobile-assigned-only",
            email="mobile-assigned-only@example.test",
            full_name="Usuario sin hojas de campo",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            email_verified_at=datetime.now(timezone.utc),
            role_id=assigned_only_role.id,
            roles=[assigned_only_role],
        )
        client = Client(client_type="persona_moral", legal_name="Cliente Mobile Scope")
        db.add_all(
            [technician_a, technician_b, unauthorized_user, assigned_only_user, client]
        )
        db.flush()

        order_a = ServiceOrder(
            folio="OSMYC-MOBILE-0001",
            work_order_number=990001,
            client_id=client.id,
            technician_id=technician_a.id,
            status="scheduled",
            requires_payment=True,
        )
        order_b = ServiceOrder(
            folio="OSMYC-MOBILE-0002",
            work_order_number=990002,
            client_id=client.id,
            technician_id=technician_b.id,
            status="scheduled",
            requires_payment=True,
        )
        unassigned_order = ServiceOrder(
            folio="OSMYC-MOBILE-0003",
            work_order_number=990003,
            client_id=client.id,
            technician_id=None,
            status="scheduled",
            requires_payment=True,
        )
        db.add_all([order_a, order_b, unassigned_order])
        db.flush()

        work_order_a = ServiceWorkOrder(
            service_order_id=order_a.id,
            sequence=1,
            work_order_number=991001,
            status="pending",
        )
        work_order_b = ServiceWorkOrder(
            service_order_id=order_b.id,
            sequence=1,
            work_order_number=991002,
            status="pending",
        )
        unassigned_work_order = ServiceWorkOrder(
            service_order_id=unassigned_order.id,
            sequence=1,
            work_order_number=991003,
            status="pending",
        )
        db.add_all([work_order_a, work_order_b, unassigned_work_order])
        db.flush()

        equipment_a = Equipment(
            service_order_id=order_a.id,
            work_order_id=work_order_a.id,
            name="Equipo A",
            status="registered",
        )
        equipment_b = Equipment(
            service_order_id=order_b.id,
            work_order_id=work_order_b.id,
            name="Equipo B",
            status="registered",
        )
        unassigned_equipment = Equipment(
            service_order_id=unassigned_order.id,
            work_order_id=unassigned_work_order.id,
            name="Equipo sin asignación",
            status="registered",
        )
        db.add_all([equipment_a, equipment_b, unassigned_equipment])
        db.flush()

        field_sheet_a = FieldSheet(
            equipment_id=equipment_a.id,
            work_order_id=work_order_a.id,
            work_order_number=work_order_a.work_order_number,
            template_key="general",
            status="draft",
        )
        field_sheet_b = FieldSheet(
            equipment_id=equipment_b.id,
            work_order_id=work_order_b.id,
            work_order_number=work_order_b.work_order_number,
            template_key="general",
            status="draft",
        )
        unassigned_field_sheet = FieldSheet(
            equipment_id=unassigned_equipment.id,
            work_order_id=unassigned_work_order.id,
            work_order_number=unassigned_work_order.work_order_number,
            template_key="general",
            status="draft",
        )
        db.add_all([field_sheet_a, field_sheet_b, unassigned_field_sheet])
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        ROLE_PERMISSIONS[assigned_only_role.name] = {"service_orders.read_assigned"}
        api = TestClient(app)
        try:
            yield {
                "api": api,
                "technician_a": technician_a,
                "technician_b": technician_b,
                "unauthorized_user": unauthorized_user,
                "assigned_only_user": assigned_only_user,
                "order_a": order_a,
                "order_b": order_b,
                "unassigned_order": unassigned_order,
                "work_order_a": work_order_a,
                "work_order_b": work_order_b,
                "unassigned_work_order": unassigned_work_order,
                "equipment_a": equipment_a,
                "equipment_b": equipment_b,
                "unassigned_equipment": unassigned_equipment,
                "field_sheet_a": field_sheet_a,
                "field_sheet_b": field_sheet_b,
                "unassigned_field_sheet": unassigned_field_sheet,
            }
        finally:
            api.close()
            app.dependency_overrides.clear()
            ROLE_PERMISSIONS.pop(assigned_only_role.name, None)

    engine.dispose()


def internal_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        extra_claims={
            "auth_context": "internal",
            "roles": [role.name for role in user.roles if role.is_active],
        },
    )
    return {"Authorization": f"Bearer {token}"}


RESOURCE_CASES = (
    ("service-orders", "order_a", "order_b", "unassigned_order"),
    ("work-orders", "work_order_a", "work_order_b", "unassigned_work_order"),
    ("equipment", "equipment_a", "equipment_b", "unassigned_equipment"),
    ("field-sheets", "field_sheet_a", "field_sheet_b", "unassigned_field_sheet"),
)


@pytest.mark.parametrize("path,own_key,foreign_key,unassigned_key", RESOURCE_CASES)
def test_technician_lists_only_assigned_resources(
    mobile_technician_context,
    path,
    own_key,
    foreign_key,
    unassigned_key,
):
    context = mobile_technician_context
    response = context["api"].get(
        f"/api/mobile/v1/technician/{path}",
        headers=internal_headers(context["technician_a"]),
    )
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()}
    assert context[own_key].id in ids
    assert context[foreign_key].id not in ids
    assert context[unassigned_key].id not in ids


@pytest.mark.parametrize("path,own_key,foreign_key,unassigned_key", RESOURCE_CASES)
def test_technician_detail_enforces_ownership_and_hides_existence(
    mobile_technician_context,
    path,
    own_key,
    foreign_key,
    unassigned_key,
):
    context = mobile_technician_context
    headers = internal_headers(context["technician_a"])
    base = f"/api/mobile/v1/technician/{path}"

    own = context["api"].get(f"{base}/{context[own_key].id}", headers=headers)
    foreign = context["api"].get(f"{base}/{context[foreign_key].id}", headers=headers)
    unassigned = context["api"].get(
        f"{base}/{context[unassigned_key].id}", headers=headers
    )

    assert own.status_code == 200, own.text
    assert own.json()["id"] == context[own_key].id
    assert foreign.status_code == 404
    assert unassigned.status_code == 404


@pytest.mark.parametrize("path,own_key,foreign_key,unassigned_key", RESOURCE_CASES)
def test_second_technician_cannot_access_first_technicians_resources(
    mobile_technician_context,
    path,
    own_key,
    foreign_key,
    unassigned_key,
):
    context = mobile_technician_context
    response = context["api"].get(
        f"/api/mobile/v1/technician/{path}/{context[own_key].id}",
        headers=internal_headers(context["technician_b"]),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("path,own_key,foreign_key,unassigned_key", RESOURCE_CASES)
def test_mobile_resources_require_authentication(
    mobile_technician_context,
    path,
    own_key,
    foreign_key,
    unassigned_key,
):
    response = mobile_technician_context["api"].get(
        f"/api/mobile/v1/technician/{path}"
    )
    assert response.status_code == 401


@pytest.mark.parametrize("path,own_key,foreign_key,unassigned_key", RESOURCE_CASES)
def test_user_without_assigned_service_permission_is_forbidden(
    mobile_technician_context,
    path,
    own_key,
    foreign_key,
    unassigned_key,
):
    context = mobile_technician_context
    response = context["api"].get(
        f"/api/mobile/v1/technician/{path}",
        headers=internal_headers(context["unauthorized_user"]),
    )
    assert response.status_code == 403


def test_field_sheets_also_require_field_sheet_read_permission(
    mobile_technician_context,
):
    context = mobile_technician_context
    response = context["api"].get(
        "/api/mobile/v1/technician/field-sheets",
        headers=internal_headers(context["assigned_only_user"]),
    )
    assert response.status_code == 403
