from dataclasses import FrozenInstanceError

import pytest

from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import ComponentKind
from app.resolution_engine.domain.exceptions import (
    InvalidResolutionDefinitionError,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)


class ExampleContextProvider:
    pass


def component_reference(
    kind: ComponentKind = ComponentKind.CONTEXT_PROVIDER,
) -> ComponentReference:
    return ComponentReference(
        kind=kind,
        key=ComponentKey(f"example.{kind.value}"),
        version=DefinitionVersion("1.0"),
        implementation=ExampleContextProvider,
    )


def test_resolution_definition_defensively_freezes_component_mapping():
    components = {
        ComponentKind.CONTEXT_PROVIDER: component_reference(),
    }
    definition = ResolutionDefinition(
        resolution_type=ResolutionType("example.resolve_case"),
        version=DefinitionVersion("1.0"),
        components=components,
    )
    components.clear()

    assert definition.component(ComponentKind.CONTEXT_PROVIDER) is not None
    with pytest.raises(TypeError):
        definition.components[ComponentKind.ANALYZER] = component_reference(  # type: ignore[index]
            ComponentKind.ANALYZER
        )
    with pytest.raises(FrozenInstanceError):
        definition.description = "changed"  # type: ignore[misc]


def test_resolution_definition_rejects_mismatched_component_kind():
    with pytest.raises(InvalidResolutionDefinitionError):
        ResolutionDefinition(
            resolution_type=ResolutionType("example.resolve_case"),
            version=DefinitionVersion("1.0"),
            components={
                ComponentKind.ANALYZER: component_reference(
                    ComponentKind.CONTEXT_PROVIDER
                )
            },
        )


def test_resolution_definition_requires_only_the_components_it_needs():
    definition = ResolutionDefinition(
        resolution_type=ResolutionType("example.resolve_case"),
        version=DefinitionVersion("1.0"),
        components={
            ComponentKind.CONTEXT_PROVIDER: component_reference(),
        },
    )

    assert definition.component(ComponentKind.ANALYZER) is None
    assert len(definition.fingerprint) == 64


def test_definition_fingerprint_changes_when_component_version_changes():
    first = ResolutionDefinition(
        resolution_type=ResolutionType("example.resolve_case"),
        version=DefinitionVersion("1.0"),
        components={
            ComponentKind.CONTEXT_PROVIDER: component_reference(),
        },
    )
    second_reference = ComponentReference(
        kind=ComponentKind.CONTEXT_PROVIDER,
        key=ComponentKey("example.context_provider"),
        version=DefinitionVersion("1.1"),
        implementation=ExampleContextProvider,
    )
    second = ResolutionDefinition(
        resolution_type=ResolutionType("example.resolve_case"),
        version=DefinitionVersion("1.0"),
        components={ComponentKind.CONTEXT_PROVIDER: second_reference},
    )

    assert first.fingerprint != second.fingerprint
