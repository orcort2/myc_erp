from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.realtime.events import eligible_communication_recipients
from app.models.user import User
from app.models.communication import (
    CommunicationConversation,
    communication_participants,
)


TEST_DATABASE_URL = (
    "postgresql+psycopg://saulcortes@127.0.0.1:5432/"
    "erp_myc_realtime_test"
)


def test_communication_authorization_lifecycle():
    engine = create_engine(TEST_DATABASE_URL)

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                assert connection.scalar(
                    text("SELECT current_database()")
                ) == "erp_myc_realtime_test"
                with Session(
                    bind=connection,
                    join_transaction_mode="rollback_only",
                    expire_on_commit=False,
                ) as db:
                    suffix = uuid4().hex[:12]

                    users = []

                    for index in range(3):
                        user = User(
                            username=f"rt_{suffix}_{index}",
                            email=f"rt_{suffix}_{index}@example.invalid",
                            full_name=f"Realtime Test {index}",
                            hashed_password="integration-test-only",
                            account_type="internal",
                            status="active",
                            is_active=True,
                        )

                        db.add(user)
                        users.append(user)

                    db.flush()

                    creator, participant, outsider = users

                    conversation = CommunicationConversation(
                        conversation_type="group",
                        title=f"Realtime integration {suffix}",
                        created_by_user_id=creator.id,
                    )

                    db.add(conversation)
                    db.flush()

                    db.execute(
                        communication_participants.insert().values(
                            conversation_id=conversation.id,
                            user_id=participant.id,
                        )
                    )

                    db.flush()

                    proposed = {
                        creator.id,
                        participant.id,
                        outsider.id,
                    }

                    class SharedSessionContext:
                        def __enter__(self):
                            return db

                        def __exit__(self, exc_type, exc_value, traceback):
                            return False

                    def eligible():
                        db.flush()
                        with patch(
                            "app.core.db.SessionLocal",
                            return_value=SharedSessionContext(),
                        ):
                            return eligible_communication_recipients(
                                conversation.id,
                                proposed,
                            )

                    # 1. Creador y participante autorizados.
                    assert eligible() == {
                        creator.id,
                        participant.id,
                    }

                    # 2. Revocacion de participante.
                    db.execute(
                        communication_participants.delete().where(
                            communication_participants.c.conversation_id
                            == conversation.id,
                            communication_participants.c.user_id
                            == participant.id,
                        )
                    )

                    db.flush()

                    assert eligible() == {creator.id}

                    # 3. Desactivacion del creador.
                    db.execute(
                        text("""
                            UPDATE users
                            SET is_active = FALSE
                            WHERE id = :user_id
                        """),
                        {"user_id": creator.id},
                    )

                    actual_active = db.scalar(
                        text("""
                            SELECT is_active
                            FROM users
                            WHERE id = :user_id
                        """),
                        {"user_id": creator.id},
                    )

                    assert actual_active is False
                    assert eligible() == set()

                    # 4. Restauracion y archivo.
                    db.execute(
                        text("""
                            UPDATE users
                            SET is_active = TRUE
                            WHERE id = :user_id
                        """),
                        {"user_id": creator.id},
                    )

                    assert eligible() == {creator.id}

                    from datetime import datetime, timezone

                    db.execute(
                        text("""
                            UPDATE communication_conversations
                            SET archived_at = CURRENT_TIMESTAMP
                            WHERE id = :conversation_id
                        """),
                        {"conversation_id": conversation.id},
                    )

                    assert db.scalar(
                        text("""
                            SELECT archived_at IS NOT NULL
                            FROM communication_conversations
                            WHERE id = :conversation_id
                        """),
                        {"conversation_id": conversation.id},
                    ) is True

                    assert eligible() == set()

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
