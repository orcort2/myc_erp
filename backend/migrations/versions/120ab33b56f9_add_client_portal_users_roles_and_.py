"""add client portal users roles and memberships

Revision ID: 120ab33b56f9
Revises: f27f8a90b1c3
Create Date: 2026-08-04 15:18:10.043270
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "120ab33b56f9"
down_revision: Union[str, None] = "f27f8a90b1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_portal_permissions",
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_client_portal_permissions_code"),
        "client_portal_permissions",
        ["code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_client_portal_permissions_module"),
        "client_portal_permissions",
        ["module"],
        unique=False,
    )

    op.create_table(
        "client_portal_roles",
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_client_portal_roles_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_client_portal_roles_client_id"),
        "client_portal_roles",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_roles_code"),
        "client_portal_roles",
        ["code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_client_portal_roles_is_system"),
        "client_portal_roles",
        ["is_system"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_roles_name"),
        "client_portal_roles",
        ["name"],
        unique=False,
    )

    op.create_table(
        "client_portal_memberships",
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "is_primary_contact",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_by", sa.Integer(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.String(length=500), nullable=True),
        sa.Column("revoked_by", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_client_portal_memberships_approved_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_client_portal_memberships_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
            name="fk_client_portal_memberships_revoked_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["suspended_by"],
            ["users.id"],
            name="fk_client_portal_memberships_suspended_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_client_portal_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id",
            "user_id",
            name="uq_client_portal_membership_client_user",
        ),
    )

    op.create_index(
        op.f("ix_client_portal_memberships_approved_by"),
        "client_portal_memberships",
        ["approved_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_client_id"),
        "client_portal_memberships",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_is_primary_contact"),
        "client_portal_memberships",
        ["is_primary_contact"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_revoked_by"),
        "client_portal_memberships",
        ["revoked_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_status"),
        "client_portal_memberships",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_suspended_by"),
        "client_portal_memberships",
        ["suspended_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_memberships_user_id"),
        "client_portal_memberships",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "client_portal_role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["client_portal_permissions.id"],
            name="fk_client_portal_role_permissions_permission_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["client_portal_roles.id"],
            name="fk_client_portal_role_permissions_role_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_client_portal_role_permission",
        ),
    )

    op.create_index(
        op.f("ix_client_portal_role_permissions_permission_id"),
        "client_portal_role_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_role_permissions_role_id"),
        "client_portal_role_permissions",
        ["role_id"],
        unique=False,
    )

    op.create_table(
        "portal_registrations",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("declared_company_name", sa.String(length=255), nullable=False),
        sa.Column("declared_company_rfc", sa.String(length=13), nullable=True),
        sa.Column("contact_phone", sa.String(length=40), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending_email_verification",
            nullable=False,
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_token_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "verification_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_internal_review_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_portal_registrations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_portal_registration_user",
        ),
    )

    op.create_index(
        op.f("ix_portal_registrations_declared_company_name"),
        "portal_registrations",
        ["declared_company_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portal_registrations_declared_company_rfc"),
        "portal_registrations",
        ["declared_company_rfc"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portal_registrations_status"),
        "portal_registrations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portal_registrations_user_id"),
        "portal_registrations",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_portal_registrations_verification_token_expires_at"),
        "portal_registrations",
        ["verification_token_expires_at"],
        unique=False,
    )

    op.create_table(
        "client_link_requests",
        sa.Column("portal_registration_id", sa.Integer(), nullable=False),
        sa.Column("proposed_client_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resulting_membership_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["portal_registration_id"],
            ["portal_registrations.id"],
            name="fk_client_link_requests_portal_registration_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_client_id"],
            ["clients.id"],
            name="fk_client_link_requests_proposed_client_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_client_link_requests_requested_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_client_link_requests_resolved_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_membership_id"],
            ["client_portal_memberships.id"],
            name="fk_client_link_requests_resulting_membership_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_client_link_requests_reviewed_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portal_registration_id",
            "proposed_client_id",
            name="uq_client_link_request_registration_client",
        ),
    )

    op.create_index(
        op.f("ix_client_link_requests_expires_at"),
        "client_link_requests",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_portal_registration_id"),
        "client_link_requests",
        ["portal_registration_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_proposed_client_id"),
        "client_link_requests",
        ["proposed_client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_requested_by"),
        "client_link_requests",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_resolved_by"),
        "client_link_requests",
        ["resolved_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_resulting_membership_id"),
        "client_link_requests",
        ["resulting_membership_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_client_link_requests_reviewed_by"),
        "client_link_requests",
        ["reviewed_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_link_requests_status"),
        "client_link_requests",
        ["status"],
        unique=False,
    )

    op.create_table(
        "client_portal_membership_roles",
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["client_portal_memberships.id"],
            name="fk_client_portal_membership_roles_membership_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["client_portal_roles.id"],
            name="fk_client_portal_membership_roles_role_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id",
            "role_id",
            name="uq_client_portal_membership_role",
        ),
    )

    op.create_index(
        op.f("ix_client_portal_membership_roles_membership_id"),
        "client_portal_membership_roles",
        ["membership_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_membership_roles_role_id"),
        "client_portal_membership_roles",
        ["role_id"],
        unique=False,
    )

    # Actualiza restricciones existentes para establecer el comportamiento
    # explícito de eliminación.
    op.drop_constraint(
        op.f("client_certificate_profiles_client_id_fkey"),
        "client_certificate_profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_client_certificate_profiles_client_id_clients",
        "client_certificate_profiles",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("client_contacts_client_id_fkey"),
        "client_contacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_client_contacts_client_id_clients",
        "client_contacts",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("user_roles_role_id_fkey"),
        "user_roles",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("user_roles_user_id_fkey"),
        "user_roles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_user_roles_user_id_users",
        "user_roles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_user_roles_role_id_roles",
        "user_roles",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # username se agrega temporalmente como nullable para soportar bases que
    # ya contengan usuarios.
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "account_type",
            sa.String(length=30),
            server_default="internal",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="active",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Genera nombres únicos para usuarios preexistentes.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET username = 'user_' || id::text
            WHERE username IS NULL
            """
        )
    )

    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=80),
        nullable=False,
    )

    op.create_index(
        op.f("ix_users_account_type"),
        "users",
        ["account_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_last_login_at"),
        "users",
        ["last_login_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_locked_until"),
        "users",
        ["locked_until"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_role_id"),
        "users",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_status"),
        "users",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_username"),
        "users",
        ["username"],
        unique=True,
    )

    op.drop_constraint(
        op.f("users_role_id_fkey"),
        "users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_users_role_id_roles",
        "users",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Los defaults anteriores sólo fueron necesarios para migrar registros
    # existentes. Las nuevas altas serán controladas por el modelo y servicio.
    op.alter_column(
        "users",
        "account_type",
        server_default=None,
        existing_type=sa.String(length=30),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "status",
        server_default=None,
        existing_type=sa.String(length=30),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "must_change_password",
        server_default=None,
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "failed_login_attempts",
        server_default=None,
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_role_id_roles",
        "users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("users_role_id_fkey"),
        "users",
        "roles",
        ["role_id"],
        ["id"],
    )

    op.drop_index(
        op.f("ix_users_username"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_status"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_role_id"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_locked_until"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_last_login_at"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_account_type"),
        table_name="users",
    )

    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "status")
    op.drop_column("users", "account_type")
    op.drop_column("users", "username")

    op.drop_constraint(
        "fk_user_roles_role_id_roles",
        "user_roles",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_user_roles_user_id_users",
        "user_roles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("user_roles_user_id_fkey"),
        "user_roles",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("user_roles_role_id_fkey"),
        "user_roles",
        "roles",
        ["role_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_client_contacts_client_id_clients",
        "client_contacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("client_contacts_client_id_fkey"),
        "client_contacts",
        "clients",
        ["client_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_client_certificate_profiles_client_id_clients",
        "client_certificate_profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("client_certificate_profiles_client_id_fkey"),
        "client_certificate_profiles",
        "clients",
        ["client_id"],
        ["id"],
    )

    op.drop_index(
        op.f("ix_client_portal_membership_roles_role_id"),
        table_name="client_portal_membership_roles",
    )
    op.drop_index(
        op.f("ix_client_portal_membership_roles_membership_id"),
        table_name="client_portal_membership_roles",
    )
    op.drop_table("client_portal_membership_roles")

    op.drop_index(
        op.f("ix_client_link_requests_status"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_reviewed_by"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_resulting_membership_id"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_resolved_by"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_requested_by"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_proposed_client_id"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_portal_registration_id"),
        table_name="client_link_requests",
    )
    op.drop_index(
        op.f("ix_client_link_requests_expires_at"),
        table_name="client_link_requests",
    )
    op.drop_table("client_link_requests")

    op.drop_index(
        op.f("ix_portal_registrations_verification_token_expires_at"),
        table_name="portal_registrations",
    )
    op.drop_index(
        op.f("ix_portal_registrations_user_id"),
        table_name="portal_registrations",
    )
    op.drop_index(
        op.f("ix_portal_registrations_status"),
        table_name="portal_registrations",
    )
    op.drop_index(
        op.f("ix_portal_registrations_declared_company_rfc"),
        table_name="portal_registrations",
    )
    op.drop_index(
        op.f("ix_portal_registrations_declared_company_name"),
        table_name="portal_registrations",
    )
    op.drop_table("portal_registrations")

    op.drop_index(
        op.f("ix_client_portal_role_permissions_role_id"),
        table_name="client_portal_role_permissions",
    )
    op.drop_index(
        op.f("ix_client_portal_role_permissions_permission_id"),
        table_name="client_portal_role_permissions",
    )
    op.drop_table("client_portal_role_permissions")

    op.drop_index(
        op.f("ix_client_portal_memberships_user_id"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_suspended_by"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_status"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_revoked_by"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_is_primary_contact"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_client_id"),
        table_name="client_portal_memberships",
    )
    op.drop_index(
        op.f("ix_client_portal_memberships_approved_by"),
        table_name="client_portal_memberships",
    )
    op.drop_table("client_portal_memberships")

    op.drop_index(
        op.f("ix_client_portal_roles_name"),
        table_name="client_portal_roles",
    )
    op.drop_index(
        op.f("ix_client_portal_roles_is_system"),
        table_name="client_portal_roles",
    )
    op.drop_index(
        op.f("ix_client_portal_roles_code"),
        table_name="client_portal_roles",
    )
    op.drop_index(
        op.f("ix_client_portal_roles_client_id"),
        table_name="client_portal_roles",
    )
    op.drop_table("client_portal_roles")

    op.drop_index(
        op.f("ix_client_portal_permissions_module"),
        table_name="client_portal_permissions",
    )
    op.drop_index(
        op.f("ix_client_portal_permissions_code"),
        table_name="client_portal_permissions",
    )
    op.drop_table("client_portal_permissions")