from app.resolution_engine.application.orchestration import (
    ResolutionOrchestrator,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import ComponentKind
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)

VERSION = DefinitionVersion("1.0")


class Context:
    component_key = ComponentKey("test.context")
    component_version = VERSION

    def build_context(self, request):
        return {"request": request}


class Analyzer:
    component_key = ComponentKey("test.analyzer")
    component_version = VERSION

    def analyze(self, context):
        return {"context": context}


class Selector:
    component_key = ComponentKey("test.selector")
    component_version = VERSION

    def select_strategy(self, *, context, analysis):
        return ("strategy", context, analysis)


class Builder:
    component_key = ComponentKey("test.builder")
    component_version = VERSION

    def build_plan(self, *, context, analysis, strategy):
        return ("plan", context, analysis, strategy)


class Simulator:
    component_key = ComponentKey("test.simulator")
    component_version = VERSION

    def simulate(self, *, context, plan):
        return ("simulation", context, plan)


class Authorization:
    component_key = ComponentKey("test.authorization")
    component_version = VERSION

    def authorization_requirements(self, *, context, plan, simulation):
        return ("authorization", context, plan, simulation)


class Revalidator:
    component_key = ComponentKey("test.revalidator")
    component_version = VERSION

    def revalidate(
        self,
        *,
        authorized_context,
        current_context,
        plan,
        simulation,
    ):
        return (
            "revalidation",
            authorized_context,
            current_context,
            plan,
            simulation,
        )


IMPLEMENTATIONS = {
    ComponentKind.CONTEXT_PROVIDER: Context,
    ComponentKind.ANALYZER: Analyzer,
    ComponentKind.STRATEGY_SELECTOR: Selector,
    ComponentKind.PLAN_BUILDER: Builder,
    ComponentKind.SIMULATOR: Simulator,
    ComponentKind.AUTHORIZATION_POLICY: Authorization,
    ComponentKind.REVALIDATOR: Revalidator,
}


class Resolver:
    def __init__(self):
        self.instances = {
            (kind, implementation.component_key, VERSION):
                implementation()
            for kind, implementation in IMPLEMENTATIONS.items()
        }

    def resolve(self, reference):
        return self.instances[
            (reference.kind, reference.key, reference.version)
        ]


def orchestrator():
    registry = ResolutionRegistry()
    registry.register(
        ResolutionDefinition(
            resolution_type=ResolutionType("example.resolve"),
            version=VERSION,
            components={
                kind: ComponentReference(
                    kind=kind,
                    key=implementation.component_key,
                    version=VERSION,
                    implementation=implementation,
                )
                for kind, implementation in IMPLEMENTATIONS.items()
            },
        )
    )
    return ResolutionOrchestrator(
        registry=registry,
        components=Resolver(),
    )


def test_orchestrator_selects_exact_registered_flow_and_coordinates_pure_stages():
    service = orchestrator()
    selection = service.selection("example.resolve", "1.0")
    context = service.build_context(
        resolution_type="example.resolve",
        definition_version="1.0",
        request="request",
    )
    analysis = service.analyze(
        resolution_type="example.resolve",
        definition_version="1.0",
        context=context,
    )
    strategy, plan = service.build_plan(
        resolution_type="example.resolve",
        definition_version="1.0",
        context=context,
        analysis=analysis,
    )
    simulation = service.simulate(
        resolution_type="example.resolve",
        definition_version="1.0",
        context=context,
        plan=plan,
    )
    requirements = service.authorization_requirements(
        resolution_type="example.resolve",
        definition_version="1.0",
        context=context,
        plan=plan,
        simulation=simulation,
    )
    result = service.revalidate(
        resolution_type="example.resolve",
        definition_version="1.0",
        authorized_context=context,
        current_context={"request": "current"},
        plan=plan,
        simulation=simulation,
    )

    assert selection.definition_version == "1.0"
    assert len(selection.definition_fingerprint) == 64
    assert strategy[0] == "strategy"
    assert requirements[0] == "authorization"
    assert result[0] == "revalidation"
    assert not hasattr(service, "execute")
