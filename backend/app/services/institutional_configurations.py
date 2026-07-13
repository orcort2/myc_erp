from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.institutional_configuration import InstitutionalConfiguration
from app.schemas.institutional_configuration import InstitutionalConfigurationUpdate
from app.services.audit_logs import write_audit_log


DEFAULT_CONFIGURATION_KEY = "default"
DEFAULT_INSTITUTIONAL_VALUES = {
    "configuration_key": DEFAULT_CONFIGURATION_KEY,
    "legal_name": "METROLOGÍA Y SERVICIOS MYC",
    "document_code": "FCA-30",
    "initial_revision": "R1",
    "address": "Av. Cristóbal Colón 6086, Int. 57, San Pedro Tlaquepaque, Jalisco, C.P. 45601",
    "phone": "33 5009 2659 · Cel. 33 1398 8169",
    "email": "contacto@mycmetrology.com.mx",
    "logo_path": "frontend/src/assets/myc-logo.png",
}


def get_or_create_institutional_configuration(db: Session) -> InstitutionalConfiguration:
    configuration = db.scalar(
        select(InstitutionalConfiguration).where(
            InstitutionalConfiguration.configuration_key == DEFAULT_CONFIGURATION_KEY
        )
    )
    if configuration is not None:
        return configuration
    configuration = InstitutionalConfiguration(**DEFAULT_INSTITUTIONAL_VALUES)
    db.add(configuration)
    db.commit()
    db.refresh(configuration)
    return configuration


def institutional_snapshot(configuration: InstitutionalConfiguration) -> dict:
    return {
        "configuration_key": configuration.configuration_key,
        "legal_name": configuration.legal_name,
        "document_code": configuration.document_code,
        "initial_revision": configuration.initial_revision,
        "address": configuration.address,
        "phone": configuration.phone,
        "email": configuration.email,
        "logo_path": configuration.logo_path,
        "configuration_updated_at": configuration.updated_at.isoformat(),
    }


def resolve_logo_path(snapshot: dict, project_root: Path) -> Path | None:
    raw_path = snapshot.get("logo_path")
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate if candidate.exists() else None


def update_institutional_configuration(
    db: Session,
    payload: InstitutionalConfigurationUpdate,
    *,
    user_id: int | None = None,
) -> InstitutionalConfiguration:
    configuration = get_or_create_institutional_configuration(db)
    previous = institutional_snapshot(configuration)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(configuration, key, value)
    write_audit_log(
        db,
        action="institutional_configuration.updated",
        entity="institutional_configurations",
        entity_id=configuration.id,
        user_id=user_id,
        previous_values=previous,
        new_values={**previous, **updates},
    )
    db.commit()
    db.refresh(configuration)
    return configuration
