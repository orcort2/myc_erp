from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.email import EmailDelivery, EmailTemplate


def test_single_alembic_head_is_the_email_migration():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["a1c4e7b9d2f6"]
    assert script.get_revision("a1c4e7b9d2f6").down_revision == "e8f1a3c5d7b9"


def test_model_matches_migration_contract():
    templates, deliveries = EmailTemplate.__table__, EmailDelivery.__table__
    assert templates.c.template_key.unique and templates.c.template_key.index
    assert {c.name for c in deliveries.constraints if c.name} >= {"ck_email_deliveries_status"}
    assert {i.name for i in deliveries.indexes} >= {"ix_email_deliveries_related_entity", "ix_email_deliveries_status", "ix_email_deliveries_template_key"}
    assert next(iter(deliveries.c.requested_by_id.foreign_keys)).target_fullname == "users.id"
    assert not any("password" in c.name or "secret" in c.name or "token" in c.name for c in deliveries.c)
