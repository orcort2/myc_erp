from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import WebSocket

from app.realtime.authentication import RealtimeIdentity
from app.realtime.contracts import RealtimeEnvelope


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def conversation_room(conversation_id: int) -> str:
    return f"conversation:{conversation_id}"


@dataclass(slots=True)
class RealtimeConnection:
    websocket: WebSocket
    user_id: int
    identity: RealtimeIdentity | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    rooms: set[str] = field(default_factory=set)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RealtimeHub(ABC):
    """Puerto de transporte; Comunicaciones no conoce la implementación física."""

    @abstractmethod
    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        *,
        identity: RealtimeIdentity | None = None,
    ) -> RealtimeConnection:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self, connection: RealtimeConnection) -> None:
        raise NotImplementedError

    @abstractmethod
    async def join(self, connection: RealtimeConnection, room: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def leave(self, connection: RealtimeConnection, room: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send(
        self, connection: RealtimeConnection, envelope: RealtimeEnvelope
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def publish(self, room: str, envelope: RealtimeEnvelope) -> int:
        raise NotImplementedError

    async def publish_to_user(
        self, user_id: int, envelope: RealtimeEnvelope
    ) -> int:
        return await self.publish(user_room(user_id), envelope)


class InMemoryRealtimeHub(RealtimeHub):
    """Hub de proceso único. No coordina workers ni instancias distintas."""

    def __init__(self) -> None:
        self._connections: dict[str, RealtimeConnection] = {}
        self._rooms: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        *,
        identity: RealtimeIdentity | None = None,
    ) -> RealtimeConnection:
        if identity is not None and identity.user_id != user_id:
            raise ValueError("La identidad no corresponde al usuario")

        connection = RealtimeConnection(
            websocket=websocket,
            user_id=user_id,
            identity=identity,
        )
        async with self._lock:
            self._connections[connection.id] = connection
            self._add_to_room(connection, user_room(user_id))
        return connection

    async def disconnect(self, connection: RealtimeConnection) -> None:
        async with self._lock:
            if self._connections.pop(connection.id, None) is None:
                return
            for room in tuple(connection.rooms):
                members = self._rooms.get(room)
                if members is None:
                    continue
                members.discard(connection.id)
                if not members:
                    self._rooms.pop(room, None)
            connection.rooms.clear()

    async def join(self, connection: RealtimeConnection, room: str) -> None:
        async with self._lock:
            if connection.id not in self._connections:
                raise RuntimeError("La conexión ya no está activa")
            self._add_to_room(connection, room)

    async def leave(self, connection: RealtimeConnection, room: str) -> None:
        async with self._lock:
            members = self._rooms.get(room)
            if members is not None:
                members.discard(connection.id)
                if not members:
                    self._rooms.pop(room, None)
            connection.rooms.discard(room)

    async def publish(self, room: str, envelope: RealtimeEnvelope) -> int:
        async with self._lock:
            recipients = [
                self._connections[connection_id]
                for connection_id in self._rooms.get(room, set())
                if connection_id in self._connections
            ]
        delivered = 0
        stale: list[RealtimeConnection] = []
        for connection in recipients:
            try:
                if room.startswith("conversation:"):
                    from app.realtime.delivery_authorization import (
                        can_deliver_conversation,
                    )
                    conversation_id = int(room.split(":", 1)[1])

                    try:
                        authorized = await asyncio.to_thread(
                            can_deliver_conversation,
                            connection,
                            conversation_id,
                        )
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception(
                            "Realtime conversation authorization failed "
                            "user_id=%s conversation_id=%s",
                            connection.user_id,
                            conversation_id,
                        )
                        continue

                    if not authorized:
                        await self.leave(connection, room)
                        continue

                if (
                    room.startswith("user:")
                    and envelope.get("event") != "resource.changed"
                    and isinstance(envelope.get("data"), dict)
                    and "conversation_id" in envelope["data"]
                ):
                    from app.realtime.delivery_authorization import (
                        can_deliver_conversation,
                    )

                    try:
                        conversation_id = int(
                            envelope["data"]["conversation_id"]
                        )
                        authorized = await asyncio.to_thread(
                            can_deliver_conversation,
                            connection,
                            conversation_id,
                        )
                    except (TypeError, ValueError):
                        authorized = False
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception(
                            "Realtime delivery authorization failed "
                            "user_id=%s",
                            connection.user_id,
                        )
                        authorized = False

                    if not authorized:
                        continue

                if (
                    room.startswith("user:")
                    and envelope.get("event") == "resource.changed"
                ):
                    from app.realtime.delivery_authorization import (
                        can_deliver_internal_resource,
                    )

                    resources = (
                        envelope.get("data", {}).get("resources")
                        if isinstance(envelope.get("data"), dict)
                        else None
                    )

                    if (
                        not isinstance(resources, list)
                        or not resources
                        or any(not isinstance(resource, str) for resource in resources)
                    ):
                        continue

                    try:
                        authorized = await asyncio.to_thread(
                            lambda: all(
                                can_deliver_internal_resource(
                                    connection,
                                    resource,
                                )
                                for resource in resources
                            )
                        )
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception(
                            "Realtime resource authorization failed "
                            "user_id=%s",
                            connection.user_id,
                        )
                        continue

                    if not authorized:
                        continue

                await self.send(connection, envelope)
                delivered += 1
            except Exception:
                stale.append(connection)
        for connection in stale:
            await self.disconnect(connection)
        return delivered

    async def send(
        self, connection: RealtimeConnection, envelope: RealtimeEnvelope
    ) -> None:
        async with connection.send_lock:
            await connection.websocket.send_json(envelope)

    def _add_to_room(self, connection: RealtimeConnection, room: str) -> None:
        self._rooms.setdefault(room, set()).add(connection.id)
        connection.rooms.add(room)

    async def active_connections(self) -> tuple[RealtimeConnection, ...]:
        async with self._lock:
            return tuple(self._connections.values())

    async def connection_count(self) -> int:
        """Métrica local útil para pruebas y diagnóstico del proceso."""

        async with self._lock:
            return len(self._connections)
