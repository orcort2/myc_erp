#!/usr/bin/env python3
"""Genera el registro maestro de archivos funcionales del ERP MYC.

No analiza ni documenta contenido sensible.  El inventario parte de los archivos
versionados y de los archivos funcionales no versionados visibles, y aplica una
lista explícita de exclusiones para no registrar artefactos de ejecución.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/PROJECT_FILE_REGISTRY.md"
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", "__pycache__", "node_modules", "dist", "build",
    "output", "tmp", "storage", "backups", "venv", ".venv",
}
EXCLUDED_NAMES = {
    ".DS_Store", "backup_erp_myc_antes_prueba.sql", "BytesIO",
    ".tmp_field_sheet_templates.json", "package-lock.json", "from", "import", "io",
    "BACKUP_ESTADO_ACTUAL (1).md",
}
EXCLUDED_PREFIXES = ("backend/resources/sat/reports/",)
OFFICIAL_IGNORED_RESOURCES = (Path("backend/resources/sat/catalogo sat.xlsx"),)
FORCE_RECLASSIFY = {
    "AGENTS.md",
    "backend/app/schemas/catalog_item.py",
    "backend/app/schemas/controlled_document.py",
    "backend/app/schemas/equipment.py",
    "backend/app/schemas/quotation.py",
    "backend/app/schemas/service_order.py",
    "backend/app/schemas/service_scope.py",
    "backend/app/services/service_order_certificate_capacity.py",
    "backend/migrations/versions/fe6f7a8b9c0d_normalize_operational_calibration_scope.py",
    "backend/tests/test_service_scope_contract.py",
    "docs/BACKUP_ESTADO_ACTUAL.md",
    "docs/architecture/CALIBRATION_SCOPE_CONTRACT.md",
    "docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md",
    "frontend/src/constants/catalog.js",
    "scripts/generate_project_file_registry.py",
    "backend/app/resolution_engine/__init__.py",
    "backend/app/resolution_engine/application/__init__.py",
    "backend/app/resolution_engine/application/action_runner.py",
    "backend/app/resolution_engine/application/execution.py",
    "backend/app/resolution_engine/application/outbox.py",
    "backend/app/resolution_engine/contracts/__init__.py",
    "backend/app/resolution_engine/contracts/execution.py",
    "backend/app/resolution_engine/domain/__init__.py",
    "backend/app/resolution_engine/domain/exceptions.py",
    "backend/app/resolution_engine/domain/execution.py",
    "backend/app/resolution_engine/domain/lifecycle.py",
    "backend/app/resolution_engine/infrastructure/__init__.py",
    "backend/app/resolution_engine/infrastructure/execution.py",
    "backend/app/resolution_engine/infrastructure/execution_control.py",
    "backend/app/resolution_engine/infrastructure/lifecycle.py",
    "backend/app/resolution_engine/infrastructure/outbox.py",
    "backend/app/resolution_engine/infrastructure/persistence/evidence.py",
    "backend/migrations/versions/c5d7e9f1a3b4_resolution_engine_phase_5_review.py",
    "backend/tests/resolution_engine/test_architecture.py",
    "backend/tests/resolution_engine/test_execution.py",
    "backend/tests/resolution_engine/test_execution_persistence.py",
    "backend/tests/resolution_engine/test_lifecycle.py",
    "backend/tests/resolution_engine/test_persistence_schema.py",
    "backend/tests/resolution_engine/test_phase_5_review_migration.py",
    "docs/architecture/resolution-engine/17_EXECUTION_RUNTIME.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_5.md",
    "backend/app/resolution_engine/application/compensation.py",
    "backend/app/resolution_engine/application/compensation_runner.py",
    "backend/app/resolution_engine/contracts/compensation.py",
    "backend/app/resolution_engine/domain/compensation.py",
    "backend/app/resolution_engine/domain/enums.py",
    "backend/app/resolution_engine/infrastructure/compensation.py",
    "backend/app/resolution_engine/infrastructure/persistence/compensation.py",
    "backend/app/resolution_engine/infrastructure/persistence/__init__.py",
    "backend/app/resolution_engine/infrastructure/persistence/core.py",
    "backend/app/resolution_engine/infrastructure/repositories.py",
    "backend/migrations/versions/d6e8f0a2b4c5_resolution_engine_phase_6_compensation.py",
    "backend/tests/resolution_engine/test_compensation.py",
    "backend/tests/resolution_engine/test_compensation_persistence.py",
    "backend/tests/resolution_engine/test_phase_6_migration.py",
    "docs/architecture/resolution-engine/18_COMPENSATION_ENGINE.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_6.md",
}
SECTION_ORDER = (
    "Backend", "Frontend", "Scripts", "Recursos", "Configuración",
    "Documentación", "Pruebas",
)


def tracked_and_visible_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    paths = {Path(line) for line in result.stdout.splitlines() if line}
    paths.update(OFFICIAL_IGNORED_RESOURCES)
    return sorted(path for path in paths if (ROOT / path).is_file() and included(path))


def included(path: Path) -> bool:
    value = path.as_posix()
    return not (
        any(part in EXCLUDED_PARTS for part in path.parts)
        or path.name in EXCLUDED_NAMES
        or value.startswith(EXCLUDED_PREFIXES)
        or path.suffix in {".pyc", ".pyo"}
    )


def section(path: Path) -> str:
    parts = path.parts
    if len(parts) > 1 and parts[0] == "backend" and parts[1] == "tests":
        return "Pruebas"
    if parts[0] == "frontend":
        return "Frontend"
    if len(parts) > 1 and parts[0] == "backend" and parts[1] == "resources":
        return "Recursos"
    if parts[0] == "scripts" or (len(parts) > 1 and parts[0] == "backend" and parts[1] == "scripts"):
        return "Scripts"
    if parts[0] == "docs" or path.name == "README.md":
        return "Documentación"
    if parts[0] == "backend" and len(parts) > 1 and parts[1] in {"app", "migrations"}:
        return "Backend"
    return "Configuración"


def words(path: Path) -> str:
    stem = path.stem.replace("_", " ").replace("-", " ")
    for old, new in {"pdfs": "PDF", "sat": "SAT", "cfdi": "CFDI", "api": "API", "ets": "ETS"}.items():
        stem = stem.replace(old, new)
    return stem


def module(path: Path) -> str:
    if path.name == "__init__.py":
        return path.parent.as_posix()
    if path.parts[0] == "backend" and len(path.parts) > 2:
        return "/".join(path.parts[:3])
    if path.parts[0] == "frontend" and len(path.parts) > 2:
        return "/".join(path.parts[:3])
    return str(path.parent) if str(path.parent) != "." else "raíz"


def classify(path: Path) -> tuple[str, str, str, str, str]:
    value = path.as_posix()
    name = path.name
    subject = words(path)
    status = "Experimental" if "/labs/" in value or "Lab" in name else "Estable"
    if "facturama" in value.lower() or name == "integrations.py":
        status = "En desarrollo"
    if "/legacy/" in value or ".pre-toolkit" in name:
        status = "Obsoleto"

    phase_4_files = {
        "backend/app/resolution_engine/contracts/lifecycle.py": (
            "Contratos de Lifecycle",
            "Declara comandos de creación y puertos explícitos para persistencia del ciclo y resolución de componentes sin acoplar el núcleo.",
            "Definiciones, ActorContext y dominio de Lifecycle",
            "Servicios de aplicación, adaptadores futuros y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/lifecycle.py": (
            "Servicio de Lifecycle",
            "Valida y crea resoluciones, reconstruye su estado y obliga a que toda transición pase por la máquina central.",
            "Registry, Clock, IdentifierFactory, LifecycleStore y state machine",
            "Composición backend futura y pruebas de Fase 4",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/orchestration.py": (
            "Orquestación interna",
            "Selecciona la definición exacta y coordina componentes puros de contexto a revalidación sin ejecutar ni publicar efectos.",
            "ResolutionRegistry, ComponentResolver y referencias versionadas",
            "Flujos internos futuros y pruebas de Fase 4",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_lifecycle_persistence.py": (
            "Pruebas de persistencia Lifecycle",
            "Verifica creación reconstruible, auditoría ordenada, incremento de versión y rechazo de escrituras obsoletas sobre SQL real en memoria.",
            "SQLAlchemy, esquema del Motor y servicio de Lifecycle",
            "Gate de persistencia y concurrencia de Fase 4",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_orchestration.py": (
            "Pruebas de orquestación",
            "Verifica selección exacta por tipo/versión y coordinación pura hasta revalidación sin exponer ejecución.",
            "Registry, componentes fake y ResolutionOrchestrator",
            "Gate de orquestación y aislamiento de Fase 4",
            "Alto",
        ),
        "docs/architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md": (
            "Contrato de Lifecycle",
            "Documenta creación, estados, transiciones, invariantes, orquestación versionada, persistencia auditada y frontera previa a ejecución.",
            "Especificación, matriz y código de Fase 4",
            "Arquitectura, desarrollo, QA y fases posteriores",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_4.md": (
            "Cierre técnico de Fase 4",
            "Registra componentes, transiciones, invariantes, exclusiones, validaciones, deuda y condición EN REVISIÓN antes de Fase 5.",
            "Implementación, arquitectura y pruebas de Fase 4",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
    }
    if value in phase_4_files:
        return phase_4_files[value]

    phase_6_files = {
        "backend/app/resolution_engine/__init__.py": (
            "API Python del Motor",
            "Expone Lifecycle, ejecución y compensación síncrona aprobados hasta Fase 6 sin acoplar transporte, ERP ni adaptadores concretos.",
            "Aplicación, contratos y dominio del Motor",
            "Bootstrap futuro e integraciones registradas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/__init__.py": (
            "API de aplicación",
            "Publica seguridad, Lifecycle, orquestación, ejecución, outbox y planificación/ejecución compensatoria.",
            "Servicios de aplicación del Motor",
            "Composición backend futura y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/compensation.py": (
            "Orquestación de compensación",
            "Planifica y ejecuta compensaciones síncronas autorizadas mediante Lifecycle, locks, checkpoints, idempotencia y resultados explícitos.",
            "CompensationEngine, CompensationRunner, CompensationStore, Clock y state machine",
            "Composición futura del Motor y pruebas de Fase 6",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/compensation_runner.py": (
            "Compensation Runner",
            "Selecciona por operation_key y constituye el único punto que invoca un CompensationHandler, convirtiendo errores o respuestas inválidas en incertidumbre.",
            "Contratos y dominio de compensación",
            "CompensationExecutor y adaptadores futuros",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/compensation.py": (
            "Contratos de compensación",
            "Declara comandos, handler y store para planificación y ejecución compensatoria sin filtrar SQL, ERP o transporte.",
            "Dominio de compensación, ActorContext, runtime y Lifecycle",
            "Aplicación, adaptadores y pruebas de Fase 6",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/__init__.py": (
            "API de contratos",
            "Expone puertos de runtime, seguridad, Lifecycle, ejecución, outbox y compensación sin filtrar infraestructura.",
            "Protocols y comandos del Motor",
            "Aplicación, adaptadores y definiciones",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/compensation.py": (
            "Dominio de compensación",
            "Modela fuente, plan, pasos, reserva, resultado y Engine determinista para inversión de orden, selección total/parcial y consolidación.",
            "Canonical hashing, ejecución, Lifecycle y enums",
            "Planner, Executor, persistencia y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/__init__.py": (
            "API de dominio",
            "Publica manifiestos, seguridad, Lifecycle, ejecución y tipos/Engine compensatorios inmutables aprobados hasta Fase 6.",
            "Módulos puros del dominio",
            "Aplicación, contratos, adaptadores y consumidores",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/enums.py": (
            "Catálogos normativos",
            "Declara estados y estrategias controlados del expediente, incluida ejecución y compensación, además de tipos persistentes de infraestructura.",
            "enum de biblioteca estándar",
            "Dominio, persistencia, Lifecycle y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/exceptions.py": (
            "Jerarquía de errores",
            "Distingue errores de definición, Lifecycle, seguridad, ejecución y compensación, incluidos handlers, idempotencia, locks e incertidumbre.",
            "Excepciones estándar",
            "Todas las capas del Motor y mapeo API futuro",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/lifecycle.py": (
            "Dominio de Lifecycle",
            "Define el grafo hasta cierres de ejecución y compensación con invariantes exactas sobre evidencia reconstruida.",
            "Enums, canonical hashing y errores del Motor",
            "Servicios, executors, adaptador SQL y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/compensation.py": (
            "Adaptador SQL de compensación",
            "Revalida actor y autorización exactos, persiste planes y checkpoints, controla locks, aplica Lifecycle y agrega auditoría/outbox en transacciones cortas.",
            "SQLAlchemy, modelos del Motor, Lifecycle y controles",
            "CompensationPlanner, CompensationExecutor y pruebas integrales",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/__init__.py": (
            "API de infraestructura",
            "Publica runtime, repositorio y adaptadores SQL de Lifecycle, ejecución, compensación, controles y outbox autorizados hasta Fase 6.",
            "Infraestructura del Motor",
            "Bootstrap futuro y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/execution_control.py": (
            "Controles SQL de exclusividad",
            "Adquiere, comprueba, renueva y libera locks tipados por token/TTL y mantiene idempotencia dentro de la transacción recibida.",
            "SQLAlchemy, locks e idempotencia persistentes",
            "Adaptadores de ejecución y compensación",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/lifecycle.py": (
            "Persistencia de Lifecycle",
            "Reconstruye evidencia de ejecución y compensación y aplica transiciones con control optimista, timestamps terminales y auditoría.",
            "SQLAlchemy, modelos persistentes y repositorio",
            "Servicios Lifecycle, executors y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/compensation.py": (
            "Modelo ORM de compensación",
            "Define planes/pasos inmutables e intentos/checkpoints no eliminables vinculados exactamente a ejecución, acción fuente y decisión de seguridad.",
            "SQLAlchemy, Base y modelos persistentes del Motor",
            "Repositorio, adaptador, Alembic y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/__init__.py": (
            "API de persistencia",
            "Expone las 26 entidades ORM vigentes, incluidas las cuatro estructuras compensatorias de Fase 6.",
            "Módulos core, planning, governance, execution, compensation y evidence",
            "Metadata global, repositorios, migraciones y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/core.py": (
            "Modelo ORM de identidad y decisión",
            "Define la raíz y evidencia inicial con el catálogo de estados extendido hasta cierres compensatorios, sin acoplamiento al ERP.",
            "SQLAlchemy, Base, enums y tipos persistentes",
            "Repositorio, Lifecycle, Alembic y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/repositories.py": (
            "Repositorio de expediente",
            "Reconstruye determinísticamente el expediente completo, incluidas las cuatro colecciones compensatorias, sin administrar transacciones o estados.",
            "SQLAlchemy Session y 26 modelos persistentes",
            "Lifecycle, servicios del Motor y pruebas",
            "Crítico",
        ),
        "backend/migrations/versions/d6e8f0a2b4c5_resolution_engine_phase_6_compensation.py": (
            "Migración de Fase 6",
            "Amplía estados raíz y crea/revierte cuatro tablas compensatorias con FKs exactas, unicidad, índices y protección histórica.",
            "Alembic, PostgreSQL y modelos ORM de compensación",
            "Despliegues, restauraciones y auditoría del Motor",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_compensation.py": (
            "Pruebas de dominio compensatorio",
            "Verifica orden/dependencias inversos, estrategias total/parcial, puntos no compensables, resúmenes e invariantes de Lifecycle.",
            "Dominio de compensación, Lifecycle y pytest",
            "Gate funcional de Fase 6",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_architecture.py": (
            "Pruebas de arquitectura",
            "Inspecciona aislamiento, dirección de capas, autoridad de Lifecycle, runners exclusivos y ausencia de workers, gateways y schedulers.",
            "ast, pathlib y paquete resolution_engine",
            "Gates arquitectónicos de Fases 1 a 6",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_compensation_persistence.py": (
            "Pruebas persistentes de compensación",
            "Verifica autorización y actor exactos incluso en replay, vínculos, duplicados, locks, incertidumbre, auditoría, outbox y reconstrucción sobre SQL.",
            "SQLAlchemy, esquema y servicios de compensación",
            "Gate de persistencia, seguridad y concurrencia de Fase 6",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_6_migration.py": (
            "Prueba de migración de Fase 6",
            "Comprueba revisión padre, simetría de cuatro tablas, estados, FKs, unicidad y triggers de la migración compensatoria.",
            "Alembic, migración d6e8f0a2b4c5 y pytest",
            "Gate de evolución reversible del esquema",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_lifecycle.py": (
            "Pruebas de Lifecycle",
            "Cubre transiciones e invariantes desde creación hasta cierres de ejecución y compensación.",
            "Dominio de Lifecycle y pytest",
            "Gate funcional y arquitectónico de Fases 4 a 6",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_persistence_schema.py": (
            "Prueba de esquema del Motor",
            "Verifica 26 tablas, relaciones, aislamiento, inmutabilidad, evidencia outbox y estructuras compensatorias.",
            "Metadata SQLAlchemy y modelos persistentes",
            "Gates de arquitectura de datos de Fases 2 a 6",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/18_COMPENSATION_ENGINE.md": (
            "Contrato del Motor de Compensación",
            "Documenta modelo declarativo, autorización, Lifecycle, ejecución síncrona, idempotencia, locks, auditoría, outbox y límites de Fase 6.",
            "Especificación, matriz y código de Fase 6",
            "Arquitectura, desarrollo, QA y fases posteriores",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_6.md": (
            "Cierre técnico de Fase 6",
            "Registra componentes, estados, invariantes, pruebas, migración, deuda, archivos clave y condición EN REVISIÓN antes de Fase 7.",
            "Implementación, arquitectura y validaciones de Fase 6",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
    }
    if value in phase_6_files:
        return phase_6_files[value]

    phase_5_files = {
        "backend/app/resolution_engine/__init__.py": (
            "API Python del Motor",
            "Expone Lifecycle y ejecución controlada aprobados hasta Fase 5 sin acoplar transporte, ERP ni adaptadores concretos.",
            "Aplicación, contratos y dominio del Motor",
            "Bootstrap futuro e integraciones registradas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/__init__.py": (
            "API de aplicación",
            "Publica seguridad, Lifecycle, orquestación, Executor, Action Runner y publicación explícita de outbox.",
            "Servicios de aplicación del Motor",
            "Composición backend futura y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/action_runner.py": (
            "Action Runner",
            "Selecciona por operation_key y constituye el único punto que invoca un ActionHandler, convirtiendo excepciones o respuestas inválidas en incertidumbre explícita.",
            "Contratos y dominio de ejecución",
            "ResolutionExecutor y adaptadores futuros",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/execution.py": (
            "Executor de resoluciones",
            "Coordina evidencia autorizada exacta, Lifecycle, idempotencia, lock, acciones y checkpoints; una pérdida de lock posterior al handler produce incertidumbre sin repetir el efecto.",
            "ExecutionEngine, ActionRunner, ExecutionStore, Clock y state machine",
            "Composición futura del Motor y pruebas de Fase 5",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/outbox.py": (
            "Publicación explícita de outbox",
            "Publica un lote solicitado y registra éxito o fallo sin scheduler, worker ni reintento.",
            "OutboxStore, EventPublisher y Clock",
            "Composición operativa futura y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/__init__.py": (
            "API de contratos",
            "Expone puertos de componentes, runtime, seguridad, Lifecycle, ejecución, acciones y outbox sin filtrar infraestructura.",
            "Protocols y comandos del Motor",
            "Aplicación, adaptadores y definiciones",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/execution.py": (
            "Contratos de ejecución",
            "Declara comando con clave idempotente interna global, handler, validación de lock, store transaccional, mensajes/publicador outbox y checkpoints desacoplados de SQL y ERP.",
            "Dominio de ejecución, ActorContext y runtime",
            "Executor y adaptadores de Fase 5/futuros",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/__init__.py": (
            "API de dominio",
            "Publica manifiestos, seguridad, Lifecycle y tipos/Engine de ejecución inmutables aprobados hasta Fase 5.",
            "Módulos puros del dominio",
            "Aplicación, contratos, adaptadores y consumidores",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/exceptions.py": (
            "Jerarquía de errores",
            "Distingue errores de definición, Lifecycle, seguridad, planes, handlers, idempotencia, locks e incertidumbre sin códigos HTTP.",
            "Excepciones estándar",
            "Todas las capas del Motor y mapeo API futuro",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/execution.py": (
            "Engine y modelo de ejecución",
            "Modela candidatos, pasos, acciones, certeza, efectos, reservas, resultados y consolidación determinista sin infraestructura ni ERP.",
            "Canonical hashing, enums y Lifecycle",
            "ResolutionExecutor, adaptadores y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/lifecycle.py": (
            "Dominio de Lifecycle",
            "Define el grafo completo hasta cierres de ejecución e invariantes exactas de plan, autorización, revalidación y conteos de pasos.",
            "Enums, canonical hashing y errores del Motor",
            "Servicios, Executor, adaptador SQL y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/__init__.py": (
            "API de infraestructura",
            "Publica runtime, repositorio y adaptadores SQL de Lifecycle, ejecución, controles y outbox autorizados hasta Fase 5.",
            "Infraestructura del Motor",
            "Bootstrap futuro y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/execution.py": (
            "Adaptador SQL de ejecución",
            "Revalida la identidad exacta resolución-plan-revalidación, comprueba el lock atómicamente y persiste checkpoints, efectos, resultados, auditoría, Lifecycle, idempotencia y outbox en transacciones cortas.",
            "SQLAlchemy, persistencia del Motor, Lifecycle y controles",
            "ResolutionExecutor y pruebas integrales",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/execution_control.py": (
            "Controles SQL de ejecución",
            "Adquiere, comprueba, renueva y libera locks por token/TTL; crea, valida y finaliza registros idempotentes dentro de una transacción recibida.",
            "SQLAlchemy, locks e idempotencia persistentes",
            "SqlAlchemyExecutionStore",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/lifecycle.py": (
            "Persistencia de Lifecycle",
            "Reconstruye evidencia hasta ejecución y aplica transiciones validadas con control optimista, timestamps terminales y auditoría.",
            "SQLAlchemy, modelos persistentes y repositorio",
            "Servicios Lifecycle, Executor y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/outbox.py": (
            "Adaptador SQL de outbox",
            "Agrega eventos en la transacción fuente y persiste publicación o fallo con fecha, intentos y error por invocación explícita, sin proceso automático.",
            "SQLAlchemy, modelo outbox y canonical hashing",
            "ExecutionStore y OutboxPublicationService",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_architecture.py": (
            "Pruebas de arquitectura",
            "Inspecciona aislamiento, dirección de capas, autoridad del Lifecycle, invocación exclusiva de handlers y ausencia de workers/gateways/schedulers.",
            "ast, pathlib y paquete resolution_engine",
            "Gates arquitectónicos de Fases 1 a 5",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_execution.py": (
            "Pruebas de ejecución",
            "Verifica Engine, orden, autorización, acciones únicas, resultados terminales, idempotencia y pérdida de lock posterior al handler sin reinvocación.",
            "Dominio/aplicación de ejecución, fakes y pytest",
            "Gate funcional de Fase 5",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_execution_persistence.py": (
            "Pruebas persistentes de ejecución",
            "Verifica sobre SQL el vínculo exacto y estable de revalidación, expiración/reemplazo de lock, checkpoints inciertos, efectos, actor, idempotencia, auditoría y fallo trazable del outbox sin retry.",
            "SQLAlchemy, esquema y servicios de ejecución",
            "Gate de persistencia/concurrencia de Fase 5",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_lifecycle.py": (
            "Pruebas de Lifecycle",
            "Cubre transiciones e invariantes desde creación hasta los cuatro cierres explícitos de ejecución.",
            "Dominio de Lifecycle y pytest",
            "Gate funcional y arquitectónico de Fases 4 y 5",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/evidence.py": (
            "Modelo ORM de evidencia",
            "Define auditoría, decisiones de seguridad, idempotencia, locks, outbox con fecha de fallo y referencias exactas del expediente y la ejecución.",
            "SQLAlchemy, Base y modelos persistentes del Motor",
            "Repositorios, adaptadores, Alembic y pruebas de esquema",
            "Crítico",
        ),
        "backend/migrations/versions/c5d7e9f1a3b4_resolution_engine_phase_5_review.py": (
            "Migración correctiva de Fase 5",
            "Agrega de forma mínima y reversible failed_at al outbox para conservar la fecha de cada decisión de publicación fallida.",
            "Alembic, PostgreSQL y modelo ResolutionOutboxEvent",
            "Despliegues, restauraciones y auditoría del Motor",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_persistence_schema.py": (
            "Prueba de esquema del Motor",
            "Verifica las tablas, relaciones, aislamiento de usuarios, inmutabilidad e incluye la evidencia temporal failed_at del outbox.",
            "Metadata SQLAlchemy y modelos persistentes",
            "Gates de arquitectura de datos de Fases 2 a 5",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_5_review_migration.py": (
            "Prueba de migración correctiva",
            "Comprueba que la revisión de Fase 5 agrega y revierte exclusivamente resolution_outbox_events.failed_at.",
            "Alembic, migración c5d7e9f1a3b4 y pytest",
            "Gate de evolución reversible del esquema del Motor",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/17_EXECUTION_RUNTIME.md": (
            "Contrato de ejecución",
            "Documenta Executor, acciones, checkpoints, idempotencia, locks, resultados, auditoría, outbox explícito y límites de Fase 5.",
            "Especificación, matriz y código de Fase 5",
            "Arquitectura, desarrollo, QA y fases posteriores",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_5.md": (
            "Cierre técnico de Fase 5",
            "Registra componentes, arquitectura, pruebas, deuda, archivos clave y aprobación correctiva que habilitó Fase 6.",
            "Implementación, arquitectura y validaciones de Fase 5",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
    }
    if value in phase_5_files:
        return phase_5_files[value]

    if "/migrations/versions/" in value:
        return ("Migración Alembic", f"Aplica la revisión {subject} del esquema y conserva la evolución reproducible de PostgreSQL.", "Alembic, modelos ORM y base de datos", "Alembic durante upgrade/downgrade y despliegues", "Crítico")
    if value == "AGENTS.md":
        return ("Normas del repositorio", "Define las reglas persistentes de cierre, respaldo, inventario, auditoría, documentación y los contratos únicos de Facturación, acreditación y Servicios Compuestos.", "Procesos de desarrollo, jerarquía documental y arquitecturas canónicas", "Agentes Codex y mantenedores del ERP", "Crítico")
    if value == "docs/BACKUP_ESTADO_ACTUAL.md":
        return ("Estado operativo vigente", "Resume exclusivamente el estado verificable actual, migraciones, validaciones y pendientes operativos, con enlaces al canon especializado.", "PROJECT_STATUS, TECHNICAL_DEBT, validaciones y migraciones vigentes", "Agentes Codex, desarrollo y operación", "Alto")
    if value == "docs/architecture/CALIBRATION_SCOPE_CONTRACT.md":
        return ("Contrato de alcance de calibración", "Define las tres claves canónicas de acreditación, su propagación automática, mapeo a certificado, validación por categoría y normalización de alias legacy.", "Schemas Pydantic, catálogo, ETS, equipos, certificados, frontend y migración", "Desarrollo de Catálogo, ETS, Captura, Calidad y Certificados", "Crítico")
    if value == "backend/app/schemas/service_scope.py":
        return ("Contrato Pydantic compartido", "Centraliza las claves de acreditación, los alcances de servicio por categoría y las leyendas persistentes sin aceptar texto documental como dominio.", "Pydantic y reglas canónicas de Catálogo/ETS", "Schemas operacionales, perfiles técnicos y servicios de certificados", "Crítico")
    if value == "backend/tests/test_service_scope_contract.py":
        return ("Prueba de contrato transversal", "Verifica las tres modalidades canónicas, rechazo de texto documental, categorías, respuestas del catálogo y mapeo bidireccional a certificados.", "Schemas de catálogo, cotización, ETS, equipo y control documental", "CI y desarrollo de la cadena de calibración", "Alto")
    if value == "backend/app/schemas/catalog_item.py":
        return ("Contrato Pydantic de Catálogo", "Valida partidas, restringe cada alcance a su categoría y consume las claves/leyendas compartidas sin aceptar contenido documental.", "service_scope.py, Pydantic y modelo CatalogItem", "Router, servicio de Catálogo, cotizaciones y frontend", "Crítico")
    if value == "backend/app/schemas/controlled_document.py":
        return ("Contrato Pydantic documental", "Valida documentos, interpretaciones y perfiles técnicos; reutiliza AccreditationScope para impedir una taxonomía paralela.", "service_scope.py, Pydantic y modelos documentales", "Control Documental, perfiles técnicos y motores operativos", "Alto")
    if value in {"backend/app/schemas/quotation.py", "backend/app/schemas/service_order.py", "backend/app/schemas/equipment.py"}:
        return ("Contrato Pydantic operacional", f"Valida payloads y respuestas de {subject}, propagando ServiceScope con las claves canónicas de acreditación.", "service_scope.py, Pydantic y modelo ORM", "Routers, servicios y cadena Catálogo→ETS→Certificado", "Alto")
    if value == "backend/app/services/service_order_certificate_capacity.py":
        return ("Capacidad automática por acreditación", "Calcula cupos del ETS, resuelve automáticamente el alcance del equipo y mapea las tres claves canónicas a tipos de certificado sin inferir desde documentos.", "Partidas ETS, equipos, certificados y service_scope.py", "Alta/edición de equipos y presentación de capacidad del ETS", "Crítico")
    if value == "backend/migrations/versions/fe6f7a8b9c0d_normalize_operational_calibration_scope.py":
        return ("Migración Alembic", "Normaliza alias legacy y texto documental a claves canónicas en seis tablas; bloquea special para evitar reclasificación silenciosa.", "Alembic, PostgreSQL y contrato calibration_scope", "Alembic durante despliegues y restauraciones", "Crítico")
    if value == "frontend/src/constants/catalog.js":
        return ("Catálogo frontend de alcances", "Expone las claves canónicas y etiquetas de acreditación propia, trazable/no acreditada y laboratorio vinculado, además de alcances por categoría.", "Contrato calibration_scope", "Catálogo y Cotizaciones", "Alto")
    if value == "docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md":
        return ("Bitácora histórica", "Conserva íntegra la cronología de entregas, respaldos, cierres y validaciones anterior a la separación del estado operativo vigente.", "Cortes y cambios históricos del ERP", "Auditorías forenses y mantenedores", "Medio")
    if value == "scripts/generate_project_file_registry.py":
        return ("Generador de inventario", "Regenera el inventario desde rutas existentes, excluye artefactos y conserva las filas previamente auditadas para no perder la revisión humana.", "Git, árbol del repositorio y PROJECT_FILE_REGISTRY", "Agentes Codex y mantenedores", "Alto")
    if value == "frontend/src/components/ets-billing/EtsBillingTab.jsx":
        return ("Composición contextual ETS", "Distingue carga contextual, ausencia resuelta y factura real; presenta el Invoice asociado con bloque estable y monta controlador/diálogo compartidos sin duplicar reglas ni APIs.", "useInvoiceWorkbenchController, InvoiceWorkbenchDialog y presentación ETS", "Pestaña Facturación de ServiceOrdersPage", "Crítico")
    if value == "frontend/src/components/ets-billing/etsInvoicePresentation.js":
        return ("Presentación de factura ETS", "Deriva etiquetas y acciones visuales de ausencia, borrador, timbrada y cancelada sin definir transiciones ni reglas backend.", "Contrato de estados vigente de Invoice", "EtsBillingTab y sus pruebas", "Alto")
    if value == "frontend/src/components/ets-billing/etsInvoicePresentation.test.js":
        return ("Prueba de presentación ETS", "Verifica que un contexto no resuelto no tenga presentación y cubre ausencia resuelta, borrador, timbrada y cancelada.", "Node test y etsInvoicePresentation", "Desarrollo y CI frontend", "Medio")
    if value == "docs/audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md":
        return ("Auditoría integral de avance", "Consolida el estado verificable de todos los módulos, sus validaciones, observaciones históricas, pendientes, riesgos, sellos y orden de cierre hacia la versión 1.0.", "Frontend, backend, base de datos, pruebas, scripts y documentación histórica", "Dirección, desarrollo, calidad, operación y futuras auditorías", "Alto")
    if name == "__init__.py":
        return ("Inicializador de paquete", f"Declara el paquete {path.parent.name} y expone las importaciones públicas que necesita su módulo.", "Módulos del mismo paquete", "Python y módulos que importan el paquete", "Medio")
    if "/models/" in value and path.suffix == ".py":
        return ("Modelo ORM", f"Define la entidad y relaciones persistentes de {subject}; es la fuente ORM de su tabla y restricciones.", "SQLAlchemy Base, migraciones y schemas", "Servicios, routers, migraciones y consultas ORM", "Crítico")
    if "/schemas/" in value and path.suffix == ".py":
        return ("Contrato Pydantic", f"Declara y valida los payloads y respuestas de API para {subject}.", "Pydantic, modelo ORM y router correspondiente", "Routers, servicios y clientes API", "Alto")
    if "/routers/" in value and path.suffix == ".py":
        return ("Router HTTP", f"Expone las operaciones HTTP de {subject}, aplica permisos y delega la operación a servicios del dominio.", "FastAPI, schemas, servicios y permisos", "app.main y clientes frontend/API", "Crítico" if name in {"auth.py", "invoices.py", "service_orders.py"} else "Alto")
    if value == "backend/app/services/invoice_pdfs.py":
        return ("Servicio de impresión CFDI", "Genera la representación impresa institucional MYC de cada factura, combina XML fiscal y configuración institucional, resuelve las nomenclaturas SAT vigentes y preserva QR, sellos, certificados y cadena original.", "Factura, XML fiscal, configuración institucional, plantilla Jinja y catálogos SAT activos", "Router de facturas y endpoint de descarga del PDF institucional", "Crítico")
    if "/services/" in value and path.suffix == ".py":
        detail = f"Implementa las reglas, validaciones y orquestación de {subject} sin acoplarlas al transporte HTTP."
        if "engine" in name:
            detail = f"Calcula y aplica las reglas especializadas del motor de {subject} para los flujos operativos."
        if "pdf" in name:
            detail = f"Construye el documento PDF de {subject} a partir de datos validados y plantillas HTML."
        if "facturama" in value:
            detail = f"Integra {subject} con Facturama: autenticación, mapeo CFDI, salud del proveedor o persistencia de evidencias según corresponda."
        return ("Servicio de aplicación", detail, "Modelos, schemas, core y dependencias del dominio", "Routers, tareas de operación y otros servicios", "Crítico" if name in {"invoices.py", "service_orders.py", "auth.py"} else "Alto")
    if value == "backend/app/templates/invoice_pdf.html":
        return ("Plantilla HTML CFDI", "Compone el imprimible institucional MYC: identidad completa del emisor, receptor, conceptos, bandas fiscales compactas y evidencias CFDI para renderizado tamaño carta.", "invoice_pdfs.py, Jinja, configuración institucional y datos fiscales resueltos", "Servicio de impresión CFDI y endpoint de PDF institucional", "Alto")
    if "/templates/" in value:
        return ("Plantilla HTML", f"Define la composición imprimible de {subject} para su renderizado a PDF.", "Servicio PDF, Jinja y datos del dominio", "Servicios de generación de documentos", "Alto")
    if value == "backend/app/main.py":
        return ("Entrada FastAPI", "Crea la aplicación FastAPI, registra routers, middleware y configuración de arranque.", "Configuración, routers y base de datos", "Uvicorn y todos los consumidores HTTP", "Crítico")
    if "/core/" in value:
        return ("Infraestructura backend", f"Centraliza la infraestructura de {subject}: configuración, seguridad, permisos, conexión o folios.", "FastAPI, SQLAlchemy y variables de entorno", "main, routers y servicios", "Crítico" if name in {"config.py", "db.py", "security.py", "permissions.py"} else "Alto")
    if "/cli/" in value:
        return ("Comando backend", f"Proporciona utilidades de línea de comandos para {subject}.", "Configuración y servicios backend", "Personal de operación y scripts", "Medio")
    if "/utils/" in value:
        return ("Paquete auxiliar", f"Expone utilidades compartidas del backend asociadas a {subject}.", "Módulos backend vecinos", "Código backend que importa el paquete", "Bajo")
    if value.startswith("backend/migrations/"):
        return ("Soporte Alembic", f"Configura o documenta la ejecución de migraciones Alembic ({subject}).", "alembic.ini y modelos ORM", "Alembic y mantenedores de base de datos", "Alto")
    if value == "backend/tests/test_invoice_documents.py":
        return ("Prueba automatizada", "Verifica nombres de descarga y que la resolución de catálogos del imprimible CFDI priorice los catálogos SAT oficiales activos.", "invoice_pdfs.py, modelos de factura y fixtures", "unittest en CI y desarrollo antes de liberar facturación", "Alto")
    if value.startswith("backend/tests/"):
        return ("Prueba automatizada", f"Verifica el contrato operativo de {subject} y previene regresiones del flujo asociado.", "Módulos backend bajo prueba y fixtures", "pytest/unittest en CI y desarrollo", "Medio")
    if value.startswith("frontend/src/pages/"):
        if name == "App.jsx":
            return ("Raíz de aplicación", "Gestiona la sesión y el enrutamiento principal de las superficies autenticadas del ERP.", "AppLayout, autenticación y rutas", "main.jsx y todas las superficies autenticadas", "Crítico")
        return ("Página React", f"Compone la pantalla de {subject}, su estado, acciones de usuario y llamadas a API.", "api.js, componentes y utilidades de presentación", "Enrutador de App y usuarios del ERP", "Alto")
    if "/components/" in value and path.suffix in {".jsx", ".js", ".css"}:
        if name == "AppLayout.jsx":
            return ("Contenedor React", "Compone la navegación, barra superior y marco visual compartido del ERP autenticado.", "App, navegación, iconos y estilos globales", "Todas las páginas mostradas dentro de AppLayout", "Alto")
        function = "Estilos de componente" if path.suffix == ".css" else "Componente React" if path.suffix == ".jsx" else "Lógica de componente"
        return (function, f"Implementa {subject}: estructura visual, interacción y/o estado reutilizable del flujo que nombra.", "Páginas React, api.js, constantes y estilos relacionados", "Páginas y componentes que importan este módulo", "Alto" if "invoice-workbench" in value or "field-sheets" in value else "Medio")
    if "/constants/" in value:
        return ("Constantes frontend", f"Centraliza los catálogos y reglas declarativas de {subject} consumidos por la interfaz.", "Páginas y componentes React", "Interfaz React que resuelve catálogos o estados", "Medio")
    if "/services/" in value and value.startswith("frontend/"):
        return ("Cliente API", "Centraliza las solicitudes al backend y normaliza los contratos consumidos por la interfaz.", "fetch/HTTP y endpoints FastAPI", "Todas las páginas y componentes que invocan API", "Crítico")
    if "/utils/" in value and value.startswith("frontend/"):
        return ("Utilidad frontend", f"Encapsula transformaciones reutilizables de {subject} para no duplicar lógica en las vistas.", "Datos de páginas y componentes", "Páginas y componentes React", "Medio")
    if value.startswith("frontend/src/"):
        if name == "global.css":
            return ("Estilos globales", "Define el sistema visual global para superficies, formularios, tablas y modales.", "Vite, AppLayout y componentes React", "Toda la interfaz frontend", "Alto")
        return ("Entrada o activo frontend", f"Sostiene el arranque o recurso visual de {subject} usado por la aplicación React.", "Vite y aplicación React", "main.jsx, App y componentes", "Alto")
    if value.startswith("scripts/") or value.startswith("backend/scripts/"):
        return ("Script operativo", f"Automatiza la operación de {subject}; debe ejecutarse como herramienta controlada del repositorio.", "Configuración, herramientas locales y backend", "Desarrollo, operación o CI según el comando", "Alto" if any(token in name for token in ("backup", "restore", "upgrade", "reset", "start")) else "Medio")
    if value.startswith("backend/resources/"):
        return ("Recurso oficial", f"Conserva la fuente o metadato oficial de {subject} para importación y trazabilidad SAT.", "Importador SAT y servicios de catálogos", "Scripts y servicios SAT", "Alto")
    if value.startswith("docs/") or name == "README.md":
        return ("Documento técnico", f"Documenta el estado, diseño, operación o decisiones de {subject} para mantenimiento verificable.", "Código y procesos descritos", "Equipo de desarrollo, operación y auditoría", "Medio")
    if name in {".gitignore", "AGENTS.md", "alembic.ini", "requirements.txt", "package.json", "vite.config.js", "index.html"} or ".env" in name:
        return ("Configuración", f"Define reglas o parámetros de {subject} requeridos para construir, ejecutar o mantener el proyecto.", "Herramientas de desarrollo y módulos del proyecto", "Entorno de ejecución, CI y mantenedores", "Crítico" if name in {"AGENTS.md", "requirements.txt", "package.json"} else "Alto")
    return ("Archivo de soporte", f"Mantiene la capacidad de {subject} dentro del proyecto.", "Módulos relacionados", "Mantenedores del proyecto", "Bajo")


def markdown_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def reviewed_rows() -> dict[str, str]:
    """Conserva filas revisadas manualmente mientras la ruta siga existiendo."""
    if not TARGET.exists():
        return {}
    rows: dict[str, str] = {}
    for line in TARGET.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        path_value = line[2:].split(" |", 1)[0]
        if path_value and path_value not in {"Ruta", "Sección"}:
            rows[path_value] = line
    return rows


def render(paths: list[Path], preserved: dict[str, str]) -> str:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        grouped[section(path)].append(path)
    lines = [
        "> Estado: VIGENTE",
        ">",
        "> Tipo: Vigente (canónico)",
        ">",
        "> Autoridad: Alta para inventario de archivos; no determina alcance, pendientes ni avance",
        ">",
        "> Prevalece sobre: inventarios manuales o listados de archivos anteriores",
        ">",
        "> Entrada documental: `project/DOCUMENTATION_INDEX.md`",
        "",
        "# Registro maestro de archivos funcionales",
        "",
        "Fecha de inventario: 2026-07-28.",
        "",
        "Este es el inventario oficial de archivos funcionales del ERP MYC. Incluye únicamente archivos fuente, configuración, migraciones, recursos oficiales, scripts, pruebas y documentación relevante. Las filas describen responsabilidad verificable; los estados reflejan el estado actual observable del repositorio.",
        "",
        "## Criterio de inclusión y mantenimiento",
        "",
        "Se excluyen artefactos generados o locales: `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `dist/`, `build/`, `output/`, `tmp/`, `storage/`, `backups/`, respaldos SQL, reportes generados y archivos de bloqueo. `backend/resources/sat/catalogo sat.xlsx` se conserva por ser fuente oficial aunque esté ignorado por Git.",
        "",
        "El inventario se regenera con `python3 scripts/generate_project_file_registry.py`. El generador no sustituye la revisión humana: al crear o cambiar un archivo debe ajustarse su responsabilidad, dependencias, consumidores, criticidad y estado antes de cerrar el trabajo.",
        "",
        "## Resumen",
        "",
        "| Sección | Archivos |",
        "| --- | ---: |",
    ]
    for key in SECTION_ORDER:
        lines.append(f"| {key} | {len(grouped[key])} |")
    lines.extend(["", "## Convenciones", "", "- **Criticidad:** Crítico (afecta integridad, seguridad o arranque), Alto (flujo principal), Medio (capacidad de soporte) y Bajo (apoyo acotado).", "- **Estado:** Estable, En desarrollo, Experimental u Obsoleto. `Obsoleto` se conserva sólo para herramientas legacy aún presentes.", ""])
    for key in SECTION_ORDER:
        lines.extend([f"## {key}", "", "| Ruta | Módulo | Función | Responsabilidad detallada | Dependencias principales | Quién utiliza el archivo | Criticidad | Estado |", "| --- | --- | --- | --- | --- | --- | --- | --- |"])
        for path in grouped[key]:
            value = path.as_posix()
            if value in preserved and value not in FORCE_RECLASSIFY:
                lines.append(preserved[value])
                continue
            function, responsibility, dependencies, consumers, criticality = classify(path)
            cells = (path.as_posix(), module(path), function, responsibility, dependencies, consumers, criticality, "Experimental" if "/labs/" in path.as_posix() or "Lab" in path.name else ("En desarrollo" if "facturama" in path.as_posix().lower() or path.name == "integrations.py" else ("Obsoleto" if "/legacy/" in path.as_posix() or ".pre-toolkit" in path.name else "Estable")))
            lines.append("| " + " | ".join(markdown_cell(cell) for cell in cells) + " |")
        lines.append("")
    lines.extend(["## Validación del inventario", "", "- El generador sólo emite rutas existentes y aplica las exclusiones descritas.", "- Antes de integrar cambios, ejecutar `python3 scripts/generate_project_file_registry.py`, revisar las filas afectadas y ejecutar `git diff --check`.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    TARGET.write_text(render(tracked_and_visible_files(), reviewed_rows()), encoding="utf-8")
