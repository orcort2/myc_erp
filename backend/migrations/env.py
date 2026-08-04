from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.db import Base
import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# PostgreSQL indexes created deliberately by historical migrations. They are
# physical access/integrity structures, not portable ORM declarations. Keeping
# this explicit allowlist prevents autogenerate from proposing destructive
# removals while every portable ORM index is still compared normally.
MIGRATION_MANAGED_INDEXES = {
    "uq_calibration_procedures_code_version_active",
    "ix_catalog_items_is_active",
    "ix_catalog_items_origin_currency",
    "uq_catalog_items_internal_key_active",
    "uq_certificates_active_field_sheet",
    "uq_controlled_document_one_active_version",
    "uq_field_sheets_active_equipment",
    "uq_reference_standard_current_certificate",
    "uq_reference_standards_internal_code_active",
    "ix_sat_catalog_records_normalized_name",
    "ix_sat_catalog_records_search_text_fts",
    "ix_sat_catalog_records_version_normalized_code_pattern",
    "ix_sat_catalog_records_version_validity",
}

# These constraints coexist intentionally with a named unique index used by
# the ORM. PostgreSQL exposes both through reflection; comparing the redundant
# constraint would otherwise propose dropping an integrity guarantee.
MIGRATION_MANAGED_UNIQUE_CONSTRAINTS = {
    "controlled_documents_code_key",
    "document_templates_template_key_key",
    "institutional_configurations_configuration_key_key",
    "sat_catalogs_code_key",
    "service_work_orders_work_order_number_key",
    "technical_profiles_code_key",
}


def include_schema_object(obj, name, type_, reflected, compare_to):
    if type_ == "index":
        columns = list(getattr(obj, "columns", ()))
        # A PostgreSQL primary key already owns a unique btree index. Some
        # legacy models/migrations additionally declared index=True on `id`;
        # those redundant physical indexes are deliberately outside drift.
        if len(columns) == 1 and bool(getattr(columns[0], "primary_key", False)):
            return False
        if reflected and compare_to is None and name in MIGRATION_MANAGED_INDEXES:
            return False
    if (
        type_ == "unique_constraint"
        and reflected
        and compare_to is None
        and name in MIGRATION_MANAGED_UNIQUE_CONSTRAINTS
    ):
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_schema_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_schema_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
