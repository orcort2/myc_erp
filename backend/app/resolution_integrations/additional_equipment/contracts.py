from __future__ import annotations

from typing import Protocol

from app.resolution_integrations.additional_equipment.domain import (
    AdditionalEquipmentFacts,
    AdditionalEquipmentOperationOutcome,
    AdditionalEquipmentResolutionRequest,
)


class AdditionalEquipmentFactsReader(Protocol):
    def read(
        self,
        request: AdditionalEquipmentResolutionRequest,
        /,
    ) -> AdditionalEquipmentFacts:
        """Obtiene hechos actuales del ETS sin producir efectos."""


class AdditionalEquipmentCommandPort(Protocol):
    def register(self, **values) -> AdditionalEquipmentOperationOutcome:
        """Registra un equipo autorizado de forma idempotente."""

    def compensate(self, **values) -> AdditionalEquipmentOperationOutcome:
        """Revierte sólo efectos todavía reversibles."""
