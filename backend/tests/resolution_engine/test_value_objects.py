import pytest

from app.resolution_engine.domain.exceptions import InvalidResolutionValueError
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)


@pytest.mark.parametrize(
    "value",
    [
        "service_order.add_equipment",
        "billing.correct_tax_data",
        "quality.release_certificate_v2",
    ],
)
def test_resolution_type_accepts_namespaced_stable_keys(value):
    assert str(ResolutionType(value)) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "single",
        "ServiceOrder.add_equipment",
        "service-order.add_equipment",
        "service_order.AddEquipment",
        ".service_order.add_equipment",
    ],
)
def test_resolution_type_rejects_mutable_or_noncanonical_keys(value):
    with pytest.raises(InvalidResolutionValueError):
        ResolutionType(value)


def test_component_key_uses_the_same_namespaced_contract():
    key = ComponentKey("service_order.context_provider")

    assert ComponentKey.parse(key) is key
    assert str(key) == "service_order.context_provider"


@pytest.mark.parametrize(
    ("value", "sort_key"),
    [
        ("0.1", (0, 1, 0)),
        ("1.0.0", (1, 0, 0)),
        ("12.34.56", (12, 34, 56)),
    ],
)
def test_definition_version_is_explicit_and_semantically_sortable(
    value,
    sort_key,
):
    version = DefinitionVersion(value)

    assert str(version) == value
    assert version.sort_key == sort_key


@pytest.mark.parametrize(
    "value",
    ["1", "v1.0", "1.0-beta", "01.0", "1.00", "1.2.3.4"],
)
def test_definition_version_rejects_ambiguous_versions(value):
    with pytest.raises(InvalidResolutionValueError):
        DefinitionVersion(value)
