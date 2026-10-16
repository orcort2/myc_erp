"""Integracion PostgreSQL de triggers de autoridad de Comunicaciones."""

from uuid import uuid4

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.communication import CommunicationConversation
from app.realtime.resource_changes import parse_resource_change


DB_NAME = "erp_myc_realtime_test"
DSN = f"postgresql://saulcortes@127.0.0.1:5432/{DB_NAME}"
SQLALCHEMY_URL = DSN.replace(
    "postgresql://", "postgresql+psycopg://", 1
)


def test_communication_authority_trigger_commit_and_rollback():
    engine = create_engine(SQLALCHEMY_URL)

    try:
        with psycopg.connect(DSN, autocommit=True) as listener:
            assert listener.execute(
                "SELECT current_database()"
            ).fetchone()[0] == DB_NAME

            listener.execute(
                "LISTEN myc_erp_resource_changes_v1"
            )

            # Fase 1: crear una conversacion y revertirla.
            with engine.connect() as connection:
                transaction = connection.begin()

                try:
                    assert connection.scalar(
                        text("SELECT current_database()")
                    ) == DB_NAME

                    with Session(
                        bind=connection,
                        join_transaction_mode="rollback_only",
                        expire_on_commit=False,
                    ) as db:
                        suffix = uuid4().hex[:12]

                        user = User(
                            username=f"rt_authority_{suffix}",
                            email=f"rt_authority_{suffix}@example.invalid",
                            full_name="Realtime Authority Test",
                            hashed_password="integration-test-only",
                            account_type="internal",
                            status="active",
                            is_active=True,
                        )
                        db.add(user)
                        db.flush()

                        conversation = CommunicationConversation(
                            conversation_type="group",
                            title="Realtime Authority Rollback Test",
                            created_by_user_id=user.id,
                        )
                        db.add(conversation)
                        db.flush()

                finally:
                    transaction.rollback()

            assert list(
                listener.notifies(timeout=0.3, stop_after=1)
            ) == [], "ROLLBACK produjo una notificacion inesperada"

            # Fase 2: comprobar el trigger con un cambio confirmado.
            # El usuario y la conversacion se crean exclusivamente
            # para esta prueba y se eliminan al finalizar.
            user_id = None
            conversation_id = None

            try:
                with Session(engine) as db:
                    suffix = uuid4().hex[:12]

                    user = User(
                        username=f"rt_authority_{suffix}",
                        email=f"rt_authority_{suffix}@example.invalid",
                        full_name="Realtime Authority Commit Test",
                        hashed_password="integration-test-only",
                        account_type="internal",
                        status="active",
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()
                    user_id = user.id

                    conversation = CommunicationConversation(
                        conversation_type="group",
                        title="Realtime Authority Commit Test",
                        created_by_user_id=user.id,
                    )
                    db.add(conversation)
                    db.flush()
                    conversation_id = conversation.id

                    db.commit()

                notifications = list(
                    listener.notifies(timeout=2, stop_after=1)
                )

                assert notifications, (
                    "PostgreSQL no emitio la notificacion"
                )

                assert any(
                    parse_resource_change(item.payload).resource
                    == "communication_authority"
                    for item in notifications
                )

            finally:
                if conversation_id is not None:
                    with engine.begin() as connection:
                        connection.execute(
                            text("""
                                DELETE FROM communication_conversations
                                WHERE id = :conversation_id
                            """),
                            {"conversation_id": conversation_id},
                        )

                if user_id is not None:
                    with engine.begin() as connection:
                        connection.execute(
                            text("""
                                DELETE FROM users
                                WHERE id = :user_id
                            """),
                            {"user_id": user_id},
                        )

    finally:
        engine.dispose()
