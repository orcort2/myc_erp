from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import WebSocket

from app.realtime.contracts import RealtimeEnvelope


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def conversation_room(conversation_id: int) -> str:
    return f"conversation:{conversation_id}"


@dataclass(slots=True)
class RealtimeConnection:
    websocket: WebSocket
    user_id: int
    id: str = field(default_factory=lambda: str(uuid4()))
    rooms: set[str] = field(default_factory=set)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RealtimeHub(ABC):
    """Puerto de transporte; Comunicaciones no conoce la implementación física."""

    @abstractmethod
    async def connect(self, websocket: WebSocket, user_id: int) -> RealtimeConnection:
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

    async def connect(self, websocket: WebSocket, user_id: int) -> RealtimeConnection:
        connection = RealtimeConnection(websocket=websocket, user_id=user_id)
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

    async def connection_count(self) -> int:
        """Métrica local útil para pruebas y diagnóstico del proceso."""

        async with self._lock:
            return len(self._connections)
