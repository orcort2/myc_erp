from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def test_single_head_is_the_password_reset_migration():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["b2d5f8a1c3e7"]
    assert script.get_revision("b2d5f8a1c3e7").down_revision == "a1c4e7b9d2f6"


def test_model_contract():
    table = PasswordResetToken.__table__
    assert table.c.token_hash.unique and table.c.token_hash.index
    assert next(iter(table.c.user_id.foreign_keys)).target_fullname == "users.id"
    assert not {"token", "plain_token", "reset_url"} & {c.name for c in table.c}
    auth_version = User.__table__.c.auth_version
    assert not auth_version.nullable and auth_version.server_default.arg == "1"
