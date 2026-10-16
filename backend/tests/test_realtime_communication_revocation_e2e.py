"""Revocacion de participantes mediante PostgreSQL NOTIFY/LISTEN."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.communication import (
    CommunicationConversation,
    communication_participants,
)
from app.models.user import User
from app.realtime.conversation_revocation import (
    revoke_invalid_conversation_rooms,
)
from app.realtime.hub import InMemoryRealtimeHub, conversation_room
from app.realtime.authentication import RealtimeIdentity
from datetime import datetime, timedelta, timezone

from app.realtime.postgres_bus import listen_invalidations
from app.realtime.resource_changes import RESOURCE_CHANGE_CHANNEL


DB_NAME = "erp_myc_realtime_test"
DSN = f"postgresql://saulcortes@127.0.0.1:5432/{DB_NAME}"
DB_URL = DSN.replace(
    "postgresql://", "postgresql+psycopg://", 1
)


def test_participant_revocation_from_postgres_notification():
    asyncio.run(_scenario())


async def _scenario():
    engine = create_engine(DB_URL)
    session_factory = sessionmaker(bind=engine)

    creator_id = None
    participant_id = None
    conversation_id = None
    listener_task = None
    stop_event = asyncio.Event()

    try:
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT current_database()")
            ) == DB_NAME

        # Crear registros exclusivos de esta prueba.
        with Session(engine) as db:
            suffix = uuid4().hex[:12]
            users = []

            for index in range(2):
                user = User(
                    username=f"rt_e2e_{suffix}_{index}",
                    email=f"rt_e2e_{suffix}_{index}@example.invalid",
                    full_name=f"Realtime E2E {index}",
                    hashed_password="integration-test-only",
                    account_type="internal",
                    status="active",
                    is_active=True,
                )
                db.add(user)
                users.append(user)

            db.flush()
            creator, participant = users

            creator_id = creator.id
            participant_id = participant.id

            conversation = CommunicationConversation(
                conversation_type="group",
                title=f"Realtime E2E {suffix}",
                created_by_user_id=creator_id,
            )
            db.add(conversation)
            db.flush()

            conversation_id = conversation.id

            db.execute(
                communication_participants.insert().values(
                    conversation_id=conversation_id,
                    user_id=participant_id,
                )
            )
            db.commit()

        hub = InMemoryRealtimeHub()

        creator_connection = await hub.connect(
            AsyncMock(), creator_id
        )
        participant_connection = await hub.connect(
            AsyncMock(), participant_id
        )

        def identity(user_id):
            return RealtimeIdentity(
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                actor_type="internal",
            )

        creator_identity = identity(creator_id)
        participant_identity = identity(participant_id)

        creator_connection.identity = creator_identity
        participant_connection.identity = participant_identity

        identities_by_socket = {
            id(creator_connection.websocket): creator_identity,
            id(participant_connection.websocket): participant_identity,
        }

        def authenticate_test_socket(db, websocket):
            return identities_by_socket[id(websocket)]

        room = conversation_room(conversation_id)

        await hub.join(creator_connection, room)
        await hub.join(participant_connection, room)

        ready = asyncio.Event()
        revoked = asyncio.Event()

        async def connection_factory():
            connection = await psycopg.AsyncConnection.connect(
                DSN, connect_timeout=5
            )
            assert (
                await (
                    await connection.execute(
                        "SELECT current_database()"
                    )
                ).fetchone()
            )[0] == DB_NAME

            # SELECT abre una transaccion implicita.
            # El listener necesita activar autocommit.
            await connection.rollback()
            return connection

        async def invalidation_handler(_event):
            return None

        async def resource_handler(change):
            if change.resource == "communication_authority":
                removed = await revoke_invalid_conversation_rooms(
                    hub
                )
                if removed:
                    revoked.set()

        # Confirmar que LISTEN esta activo antes del DELETE.
        # La conexion de escucha se inicia dentro de la tarea.
        async def monitored_factory():
            connection = await connection_factory()
            ready.set()
            return connection

        with (
            patch(
                "app.realtime.delivery_authorization.SessionLocal",
                session_factory,
            ),
            patch(
                "app.realtime.delivery_authorization.authenticate_websocket",
                side_effect=authenticate_test_socket,
            ),
        ):
            listener_task = asyncio.create_task(
                listen_invalidations(
                    monitored_factory,
                    invalidation_handler,
                    stop_event=stop_event,
                    resource_handler=resource_handler,
                )
            )

            await asyncio.wait_for(ready.wait(), timeout=5)
            await asyncio.sleep(0.2)

            # Eliminar al participante y confirmar la transaccion.
            with engine.begin() as connection:
                connection.execute(
                    communication_participants.delete().where(
                        communication_participants.c.conversation_id
                        == conversation_id,
                        communication_participants.c.user_id
                        == participant_id,
                    )
                )

            await asyncio.wait_for(revoked.wait(), timeout=5)

        assert room in creator_connection.rooms
        assert room not in participant_connection.rooms
        assert f"user:{participant_id}" in participant_connection.rooms
        assert await hub.connection_count() == 2

    finally:
        stop_event.set()

        if listener_task is not None:
            try:
                await asyncio.wait_for(
                    listener_task, timeout=4
                )
            except asyncio.TimeoutError:
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass

        # Limpiar exclusivamente los registros creados por esta prueba.
        if conversation_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("""
                        DELETE FROM communication_conversations
                        WHERE id = :id
                    """),
                    {"id": conversation_id},
                )

        for user_id in (participant_id, creator_id):
            if user_id is not None:
                with engine.begin() as connection:
                    connection.execute(
                        text("DELETE FROM users WHERE id = :id"),
                        {"id": user_id},
                    )

        engine.dispose()
