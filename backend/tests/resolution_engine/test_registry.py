import pytest

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import ComponentKind
from app.resolution_engine.domain.exceptions import (
    DuplicateResolutionDefinitionError,
    NoActiveResolutionDefinitionError,
    ResolutionDefinitionNotFoundError,
    ResolutionRegistryFrozenError,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)


class VersionOneProvider:
    pass


class VersionTwoProvider:
    pass


def definition(version: str, implementation: type) -> ResolutionDefinition:
    return ResolutionDefinition(
        resolution_type=ResolutionType("service_order.add_equipment"),
        version=DefinitionVersion(version),
        components={
            ComponentKind.CONTEXT_PROVIDER: ComponentReference(
                kind=ComponentKind.CONTEXT_PROVIDER,
                key=ComponentKey("service_order.add_equipment_context"),
                version=DefinitionVersion(version),
                implementation=implementation,
            )
        },
    )


def test_new_resolution_type_is_registered_without_modifying_registry_core():
    registry = ResolutionRegistry()
    expected = definition("1.0", VersionOneProvider)

    registry.register(expected)

    assert registry.resolve("service_order.add_equipment") is expected
    assert registry.resolve("service_order.add_equipment", "1.0") is expected


def test_multiple_versions_coexist_and_historical_version_remains_resolvable():
    registry = ResolutionRegistry()
    version_one = definition("1.0", VersionOneProvider)
    version_two = definition("2.0", VersionTwoProvider)

    registry.register(version_one)
    registry.register(version_two)

    assert registry.resolve("service_order.add_equipment") is version_two
    assert registry.resolve("service_order.add_equipment", "1.0") is version_one
    assert registry.registered_versions("service_order.add_equipment") == (
        DefinitionVersion("1.0"),
        DefinitionVersion("2.0"),
    )


def test_historical_definition_can_be_registered_without_becoming_active():
    registry = ResolutionRegistry()
    historical = definition("1.0", VersionOneProvider)

    registry.register(historical, activate=False)

    assert registry.resolve(
        "service_order.add_equipment", "1.0"
    ) is historical
    with pytest.raises(NoActiveResolutionDefinitionError):
        registry.resolve("service_order.add_equipment")


def test_active_version_can_be_selected_explicitly():
    registry = ResolutionRegistry()
    version_one = definition("1.0", VersionOneProvider)
    version_two = definition("2.0", VersionTwoProvider)
    registry.register(version_one)
    registry.register(version_two)

    registry.activate("service_order.add_equipment", "1.0")

    assert registry.resolve("service_order.add_equipment") is version_one


def test_duplicate_registration_is_rejected_even_if_definition_matches():
    registry = ResolutionRegistry()
    expected = definition("1.0", VersionOneProvider)
    registry.register(expected)

    with pytest.raises(DuplicateResolutionDefinitionError):
        registry.register(expected)


def test_unknown_exact_version_is_reported_explicitly():
    registry = ResolutionRegistry()
    registry.register(definition("1.0", VersionOneProvider))

    with pytest.raises(ResolutionDefinitionNotFoundError):
        registry.resolve("service_order.add_equipment", "9.0")


def test_frozen_registry_preserves_reads_and_rejects_mutations():
    registry = ResolutionRegistry()
    expected = definition("1.0", VersionOneProvider)
    registry.register(expected)
    registry.freeze()

    assert registry.resolve("service_order.add_equipment") is expected
    with pytest.raises(ResolutionRegistryFrozenError):
        registry.register(definition("2.0", VersionTwoProvider))
    with pytest.raises(ResolutionRegistryFrozenError):
        registry.activate("service_order.add_equipment", "1.0")


def test_definition_listing_is_deterministic():
    registry = ResolutionRegistry()
    registry.register(definition("2.0", VersionTwoProvider))
    registry.register(definition("1.0", VersionOneProvider))

    assert [
        str(item.version) for item in registry.list_definitions()
    ] == ["1.0", "2.0"]
