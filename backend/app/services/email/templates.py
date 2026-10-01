"""Persistent template access: idempotent defaults, safe updates."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email import EmailTemplate
from app.services.audit_logs import write_audit_log
from app.services.email.catalog import TEMPLATE_DEFINITIONS, TemplateDefinition
from app.services.email.errors import EmailTemplateError
from app.services.email.renderer import validate_template_text


def get_definition(template_key: str) -> TemplateDefinition:
    try:
        return TEMPLATE_DEFINITIONS[template_key]
    except KeyError as exc:
        raise EmailTemplateError(f"Plantilla de correo desconocida: {template_key[:60]!r}.") from exc


def ensure_default_templates(db: Session) -> None:
    """Create missing defaults only; never overwrites edited content."""
    existing = set(db.scalars(select(EmailTemplate.template_key)).all())
    created = False
    for definition in TEMPLATE_DEFINITIONS.values():
        if definition.key not in existing:
            db.add(
                EmailTemplate(
                    template_key=definition.key,
                    name=definition.name,
                    subject_template=definition.subject,
                    body_template=definition.body,
                )
            )
            created = True
    if created:
        db.commit()


def list_templates(db: Session) -> list[EmailTemplate]:
    ensure_default_templates(db)
    return list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.template_key)).all())


def get_template(db: Session, template_key: str) -> EmailTemplate:
    get_definition(template_key)
    ensure_default_templates(db)
    return db.scalar(select(EmailTemplate).where(EmailTemplate.template_key == template_key))


def update_template(
    db: Session,
    template_key: str,
    *,
    actor_id: int,
    name: str | None = None,
    subject_template: str | None = None,
    body_template: str | None = None,
    is_active: bool | None = None,
) -> EmailTemplate:
    definition = get_definition(template_key)
    template = get_template(db, template_key)
    new_subject = template.subject_template if subject_template is None else subject_template.strip()
    new_body = template.body_template if body_template is None else body_template.strip()
    if not new_subject or not new_body:
        raise EmailTemplateError("El asunto y el cuerpo no pueden estar vacíos.")
    validate_template_text(definition, new_subject, new_body)
    changed = {
        key: value
        for key, value in {
            "name": name,
            "subject_template": subject_template and new_subject,
            "body_template": body_template and new_body,
            "is_active": is_active,
        }.items()
        if value is not None
    }
    template.subject_template, template.body_template = new_subject, new_body
    if name is not None:
        template.name = name.strip()
    if is_active is not None:
        template.is_active = is_active
    write_audit_log(
        db,
        action="email.template.updated",
        entity="email_templates",
        entity_id=template.id,
        user_id=actor_id,
        new_values={"template_key": template_key, "fields": sorted(changed)},
    )
    db.commit()
    return template
