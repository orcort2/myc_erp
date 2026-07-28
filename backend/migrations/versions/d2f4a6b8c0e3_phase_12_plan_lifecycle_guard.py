"""Allow controlled plan status transitions required by the canonical Lifecycle.

Revision ID: d2f4a6b8c0e3
Revises: c1e3f5a7b9d2
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op


revision: str = "d2f4a6b8c0e3"
down_revision: str | None = "c1e3f5a7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION resolution_engine_guard_plan_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.resolution_id IS DISTINCT FROM OLD.resolution_id
               OR NEW.strategy_selection_id IS DISTINCT FROM OLD.strategy_selection_id
               OR NEW.context_snapshot_id IS DISTINCT FROM OLD.context_snapshot_id
               OR NEW.version IS DISTINCT FROM OLD.version
               OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
               OR NEW.summary IS DISTINCT FROM OLD.summary
               OR NEW.rationale IS DISTINCT FROM OLD.rationale
               OR NEW.expected_impact IS DISTINCT FROM OLD.expected_impact
               OR NEW.preserved_entities IS DISTINCT FROM OLD.preserved_entities
               OR NEW.warnings IS DISTINCT FROM OLD.warnings
               OR NEW.blockers IS DISTINCT FROM OLD.blockers
               OR NEW.authorization_requirements IS DISTINCT FROM OLD.authorization_requirements
               OR NEW.plan_hash IS DISTINCT FROM OLD.plan_hash
               OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
               OR NEW.activated_at IS DISTINCT FROM OLD.activated_at
            THEN
                RAISE EXCEPTION 'plan identity and content are immutable'
                    USING ERRCODE = '55000';
            END IF;

            IF NEW.status IS DISTINCT FROM OLD.status
               AND (OLD.status, NEW.status) NOT IN (
                   ('draft', 'ready'),
                   ('ready', 'simulated'),
                   ('ready', 'invalidated'),
                   ('ready', 'superseded'),
                   ('ready', 'cancelled'),
                   ('simulated', 'pending_authorization'),
                   ('simulated', 'authorized'),
                   ('simulated', 'invalidated'),
                   ('simulated', 'cancelled'),
                   ('pending_authorization', 'authorized'),
                   ('pending_authorization', 'invalidated'),
                   ('pending_authorization', 'cancelled'),
                   ('authorized', 'executing'),
                   ('authorized', 'invalidated'),
                   ('authorized', 'cancelled'),
                   ('executing', 'executed'),
                   ('executing', 'failed')
               )
            THEN
                RAISE EXCEPTION 'invalid plan status transition % -> %',
                    OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;

            IF NEW.is_active IS DISTINCT FROM OLD.is_active
               AND NOT (
                   OLD.is_active = true
                   AND NEW.is_active = false
                   AND NEW.status IN (
                       'invalidated', 'superseded', 'cancelled'
                   )
               )
            THEN
                RAISE EXCEPTION 'invalid plan activation change'
                    USING ERRCODE = '55000';
            END IF;

            IF (
                NEW.invalidated_at IS DISTINCT FROM OLD.invalidated_at
                OR NEW.invalidation_reason IS DISTINCT FROM OLD.invalidation_reason
               )
               AND NEW.status NOT IN (
                   'invalidated', 'superseded', 'cancelled'
               )
            THEN
                RAISE EXCEPTION 'invalid plan invalidation metadata'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION resolution_engine_guard_plan_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status <> 'draft' THEN
                RAISE EXCEPTION 'plan % is immutable after draft', OLD.id
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.resolution_id IS DISTINCT FROM OLD.resolution_id
               OR NEW.version IS DISTINCT FROM OLD.version THEN
                RAISE EXCEPTION 'plan identity and version are immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
