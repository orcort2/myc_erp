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
    "myc-mobile-sdk57-backup",
}
EXCLUDED_NAMES = {
    ".DS_Store", "backup_erp_myc_antes_prueba.sql", "BytesIO",
    ".tmp_field_sheet_templates.json", "package-lock.json", "from", "import", "io",
    "BACKUP_ESTADO_ACTUAL (1).md", "resolution_engine.zip",
    "backend.zip",
}
EXCLUDED_PREFIXES = ("backend/resources/sat/reports/",)
OFFICIAL_IGNORED_RESOURCES = (Path("backend/resources/sat/catalogo sat.xlsx"),)
FORCE_RECLASSIFY = {
    "AGENTS.md",
    "backend/app/main.py",
    "backend/app/models/lab_work_order.py",
    "backend/app/routers/lab_work_orders.py",
    "backend/app/schemas/lab_work_order.py",
    "backend/app/services/lab_work_order_pdfs.py",
    "backend/app/services/lab_work_orders.py",
    "backend/migrations/versions/c6e8a1b4d2f9_create_lab_work_orders.py",
    "backend/tests/test_lab_work_orders.py",
    "docs/architecture/LAB_WORK_ORDERS.md",
    "docs/closures/LAB_WORK_ORDERS_VERTICAL_SLICE_2026-08-13.md",
    "myc-mobile/app/(auth)/login.tsx",
    "myc-mobile/app/(technician)/index.tsx",
    "myc-mobile/app/(technician)/work-orders.tsx",
    "myc-mobile/src/api/client.ts",
    "myc-mobile/src/auth/AuthProvider.tsx",
    "myc-mobile/src/components/SignaturePad.tsx",
    "myc-mobile/src/config/environment.ts",
    "myc-mobile/src/services/auth.service.ts",
    "myc-mobile/src/storage/secure-storage.ts",
    "myc-mobile/src/types/auth.ts",
    "myc-mobile/src/types/lab-work-order.ts",
    "backend/app/models/__init__.py",
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
    "backend/app/routers/certificates.py",
    "backend/app/services/certificate_authentication.py",
    "backend/app/services/certificates.py",
    "backend/tests/test_certificate_authentication_integrity.py",
    "docs/closures/CERTIFICATE_AUTHENTICATION_INTEGRITY_SPRINT_2026-08-10.md",
    "frontend/src/pages/ServiceOrdersPage.jsx",
    "frontend/src/pages/certificateAuthenticationAuthority.test.js",
    "backend/app/core/permissions.py",
    "backend/app/core/portal/constants.py",
    "backend/app/core/portal/security.py",
    "backend/app/routers/reference_standard_certificates.py",
    "backend/app/security/api_access.py",
    "backend/app/services/portal/permission_service.py",
    "backend/tests/test_capability_gate_reconciliation.py",
    "backend/tests/test_client_portal_integration.py",
    "docs/closures/TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md",
    "frontend/src/portal/ClientPortalLayout.jsx",
    "frontend/src/portal/portalCapability.test.js",
    "scripts/validate_capability_catalog.py",
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
    "docs/architecture/resolution-engine/19_PHASE_7_OPENING.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_6.md",
    "backend/app/resolution_engine/application/audit.py",
    "backend/app/resolution_engine/contracts/audit.py",
    "backend/app/resolution_engine/domain/audit.py",
    "backend/app/resolution_engine/infrastructure/audit.py",
    "backend/app/resolution_engine/infrastructure/audit_projection.py",
    "backend/app/resolution_engine/infrastructure/security.py",
    "backend/tests/resolution_engine/test_audit.py",
    "backend/tests/resolution_engine/test_audit_persistence.py",
    "docs/architecture/resolution-engine/20_AUDIT_EVIDENCE.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_7.md",
    "backend/app/resolution_engine/application/security.py",
    "backend/app/resolution_engine/contracts/lifecycle.py",
    "backend/app/resolution_engine/domain/security.py",
    "backend/app/resolution_engine/infrastructure/security_decisions.py",
    "backend/migrations/versions/e7f9a1b3c5d7_resolution_engine_phase_8_security.py",
    "backend/migrations/versions/f8a0b2c4d6e8_phase_8_security_decision_replay.py",
    "backend/tests/resolution_engine/test_phase_8_security.py",
    "docs/architecture/resolution-engine/21_PHASE_8_OPENING.md",
    "docs/architecture/resolution-engine/22_INTEGRAL_SECURITY.md",
    "docs/architecture/resolution-engine/23_PHASE_9_OPENING.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_8.md",
    "backend/app/resolution_engine/contracts/audit.py",
    "backend/app/resolution_engine/infrastructure/audit.py",
    "backend/app/resolution_engine/infrastructure/persistence/execution.py",
    "backend/app/models/certificate_resolution_operation.py",
    "backend/app/resolution_integrations/__init__.py",
    "backend/app/resolution_integrations/certificates/__init__.py",
    "backend/app/resolution_integrations/certificates/application.py",
    "backend/app/resolution_integrations/certificates/contracts.py",
    "backend/app/resolution_integrations/certificates/domain.py",
    "backend/app/resolution_integrations/certificates/infrastructure.py",
    "backend/app/services/certificate_resolution_operations.py",
    "backend/migrations/versions/f9c1d3e5a7b9_phase_9_certificates_integration.py",
    "backend/tests/resolution_engine/test_phase_9_certificates.py",
    "docs/architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md",
    "docs/architecture/resolution-engine/25_PHASE_10_OPENING.md",
    "docs/architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md",
    "docs/architecture/resolution-engine/README.MD",
    "docs/closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md",
    "docs/modules/calidad/AUTENTICACION_CERTIFICADOS.md",
    "backend/app/models/resolution_api_consumer.py",
    "backend/app/resolution_public_api/__init__.py",
    "backend/app/resolution_public_api/application.py",
    "backend/app/resolution_public_api/cursor.py",
    "backend/app/resolution_public_api/errors.py",
    "backend/app/resolution_public_api/security.py",
    "backend/app/routers/resolution_public_api.py",
    "backend/migrations/versions/a0d2f4b6c8e1_phase_10_public_api_consumers.py",
    "backend/myc_resolution_contracts/__init__.py",
    "backend/myc_resolution_contracts/v1.py",
    "backend/myc_resolution_sdk/__init__.py",
    "backend/myc_resolution_sdk/client.py",
    "backend/myc_resolution_sdk/errors.py",
    "backend/tests/resolution_engine/test_phase_10_public_api.py",
    "docs/architecture/resolution-engine/26_PUBLIC_API_SDK.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_10.md",
    "backend/app/resolution_engine/application/distribution.py",
    "backend/app/resolution_engine/contracts/distribution.py",
    "backend/app/resolution_engine/domain/distribution.py",
    "backend/app/resolution_engine/infrastructure/distribution.py",
    "backend/app/resolution_engine/infrastructure/persistence/distribution.py",
    "backend/migrations/versions/c1e3f5a7b9d2_phase_11_distributed_runtime.py",
    "backend/tests/resolution_engine/test_phase_11_distributed_runtime.py",
    "docs/architecture/resolution-engine/27_PHASE_11_OPENING.md",
    "docs/architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_11.md",
    "backend/app/core/config.py",
    "backend/app/core/permissions.py",
    "backend/app/resolution_center/__init__.py",
    "backend/app/resolution_center/actor.py",
    "backend/app/resolution_center/definitions.py",
    "backend/app/resolution_center/query.py",
    "backend/app/resolution_center/schemas.py",
    "backend/app/resolution_center/worker.py",
    "backend/app/resolution_center/workflow.py",
    "backend/app/routers/resolution_center.py",
    "backend/migrations/versions/d2f4a6b8c0e3_phase_12_plan_lifecycle_guard.py",
    "backend/tests/resolution_engine/test_phase_12_resolution_center.py",
    "backend/tests/resolution_engine/test_phase_13_resolution_center_consolidation.py",
    "frontend/src/constants/navigation.js",
    "frontend/src/pages/resolution-center.css",
    "frontend/src/services/api.js",
    "frontend/src/utils/resolutionCenter.js",
    "frontend/src/utils/resolutionCenter.test.js",
    "docs/architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md",
    "docs/architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_12.md",
    "docs/closures/RESOLUTION_ENGINE_PHASE_13.md",
    "backend/app/core/permissions.py",
    "backend/app/main.py",
    "backend/app/models/__init__.py",
    "backend/app/models/quotation_service_change.py",
    "backend/app/routers/quotation_service_changes.py",
    "backend/app/schemas/quotation_service_change.py",
    "backend/app/services/quotation_service_changes.py",
    "backend/app/services/quotations.py",
    "backend/migrations/versions/9d0e1f2a3b4c_quotation_service_change_exception.py",
    "backend/tests/test_quotation_service_change_exception.py",
    "frontend/src/components/sales/QuotationServiceExceptions.jsx",
    "frontend/src/components/sales/quotation-service-exceptions.css",
    "frontend/src/pages/QuotationsPage.jsx",
    "frontend/src/services/api.js",
    "frontend/src/utils/quotationServiceExceptions.js",
    "frontend/src/utils/quotationServiceExceptions.test.js",
    "docs/architecture/sales/QUOTATION_CHANGE_SERVICE_EXCEPTION.md",
    "docs/closures/QUOTATION_CHANGE_SERVICE_EXCEPTION.md",
}
FORCE_RECLASSIFY.update({
    "backend/app/core/folios.py",
    "backend/app/core/permissions.py",
    "backend/app/models/__init__.py",
    "backend/app/models/catalog_item.py",
    "backend/app/models/equipment.py",
    "backend/app/models/folio_sequence.py",
    "backend/app/models/linked_company.py",
    "backend/app/models/quotation_service_change.py",
    "backend/app/models/service_order.py",
    "backend/app/routers/catalog_items.py",
    "backend/app/routers/quotation_service_changes.py",
    "backend/app/schemas/catalog_item.py",
    "backend/app/schemas/equipment.py",
    "backend/app/schemas/quotation_service_change.py",
    "backend/app/schemas/service_order.py",
    "backend/app/schemas/service_type.py",
    "backend/app/services/catalog_items.py",
    "backend/app/services/certificates.py",
    "backend/app/services/equipment.py",
    "backend/app/services/folio_engine.py",
    "backend/app/services/institutional_folios.py",
    "backend/app/services/quotation_revision_diff.py",
    "backend/app/services/quotation_service_changes.py",
    "backend/app/services/quotations.py",
    "backend/app/services/service_order_rebuilds.py",
    "backend/app/services/service_orders.py",
    "backend/migrations/versions/ae1f2a3b4c5d_controlled_unlock_service_types_folios.py",
    "backend/migrations/versions/af2a3b4c5d6e_service_order_source_snapshot_constraints.py",
    "backend/migrations/versions/b03b4c5d6e7f_initialize_2026_institutional_sequences.py",
    "backend/tests/test_quotation_service_change_exception.py",
    "docs/architecture/folios/CERTIFICATE_AND_WORK_ORDER_FOLIOS.md",
    "docs/architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md",
    "docs/architecture/services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md",
    "docs/closures/SALES_UNLOCK_AND_SERVICE_TYPES_2026-07-29.md",
    "frontend/src/components/sales/QuotationServiceExceptions.jsx",
    "frontend/src/components/sales/quotation-service-exceptions.css",
    "frontend/src/components/service-order-exceptions.css",
    "frontend/src/constants/forms.js",
    "frontend/src/pages/QuotationsPage.jsx",
    "frontend/src/services/api.js",
    "frontend/src/utils/exceptionAuthority.js",
    "frontend/src/utils/exceptionAuthority.test.js",
    "frontend/src/styles/global.css",
    "frontend/src/utils/quotationServiceExceptions.js",
    "frontend/src/utils/quotationServiceExceptions.test.js",
})
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
        # Copias locales creadas por el sistema con sufijo " 2" no son
        # archivos funcionales ni deben contaminar inventario o validaciones.
        or any(Path(part).stem.endswith(" 2") for part in path.parts)
        or path.name in EXCLUDED_NAMES
        or value.startswith(EXCLUDED_PREFIXES)
        or path.suffix in {".pyc", ".pyo", ".zip"}
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

    lab_files = {
        "backend/app/models/lab_work_order.py": ("Agregado persistente OT LAB", "Modela OT, equipos, sesión de firma compartida y firmas sin FKs a dominios productivos.", "SQLAlchemy, users e infraestructura de folios", "Servicio LAB, Alembic, PDF, exportación y pruebas", "Crítico"),
        "backend/app/routers/lab_work_orders.py": ("API móvil OT LAB", "Expone CRUD temporal, adicionales, firma grupal, cierre, PDF y exportación bajo permisos explícitos.", "FastAPI, schemas, servicio LAB y auth interno", "myc-mobile y exportación administrativa", "Crítico"),
        "backend/app/schemas/lab_work_order.py": ("Contrato OT LAB", "Valida datos generales, equipos sin modelo, firmas PNG y respuestas agrupadas.", "Pydantic y modelos LAB", "Router, servicio y cliente móvil", "Alto"),
        "backend/app/services/lab_work_orders.py": ("Dominio OT LAB", "Orquesta folios 6400–6999, máximo 10, cadena adicional, firma única, bloqueo, cierre, auditoría y exportación verificable.", "SQLAlchemy, audit, PDF e institutional_folio_sequences", "Router LAB, pruebas y retiro futuro", "Crítico"),
        "backend/app/services/lab_work_order_pdfs.py": ("PDF institucional OT LAB", "Adapta datos LAB al render institucional, separa domicilio/C.P./ciudad/estado y normaliza la orden de compra opcional.", "WeasyPrint y work_order_pdfs", "Cierre grupal, descarga y exportación", "Alto"),
        "backend/app/services/work_order_pdfs.py": ("Render institucional de OT", "Compone el contexto productivo y admite overrides explícitos de dirección desglosada usados sólo por el adaptador LAB.", "Jinja, modelos productivos y plantilla work_order_pdf", "Generadores PDF productivo y LAB", "Alto"),
        "backend/app/templates/work_order_pdf.html": ("Plantilla institucional de OT", "Renderiza la cuadrícula institucional, incluidos valores independientes de domicilio, C.P., ciudad y estado cuando el adaptador los aporta.", "Jinja y work_order_pdfs", "PDF de OT productiva y temporal LAB", "Alto"),
        "backend/migrations/versions/c6e8a1b4d2f9_create_lab_work_orders.py": ("Migración OT LAB", "Fusiona los dos heads preservados y crea exclusivamente las cuatro tablas LAB, restricciones, índices y FKs trazables.", "Alembic, PostgreSQL, a7c2e5f8b1d4 y fdc1c503a353", "Despliegue, rollback y validación de esquema", "Crítico"),
        "backend/tests/test_lab_work_orders.py": ("Suite OT LAB", "Prueba permisos, folios, límite, adicionales, firma compartida, bloqueo, mapeo PDF, vacíos y exportación.", "Pytest, TestClient, pypdf y SQLite aislado", "Gate backend del vertical LAB", "Crítico"),
        "myc-mobile/app/(technician)/work-orders.tsx": ("Flujo móvil OT LAB", "Implementa captura agrupada con safe area, equipos, revisión, firma única, cierre, impresión y compartir en iPhone.", "Expo Router, SafeAreaContext, AuthProvider, FileSystem, Print y Sharing", "Técnicos autorizados en Expo Go", "Crítico"),
        "myc-mobile/app/_layout.tsx": ("Raíz de navegación móvil", "Provee safe area real a todas las rutas y mantiene la sesión autenticada alrededor del Stack de Expo Router.", "Expo Router, SafeAreaProvider y AuthProvider", "Todas las pantallas móviles", "Crítico"),
        "myc-mobile/src/components/SignaturePad.tsx": ("Firma táctil Expo Go", "Captura, limpia y confirma trazos PNG en un panel móvil espaciado mediante canvas WebView sin módulo nativo.", "react-native-webview", "Flujo de firma grupal OT LAB", "Alto"),
        "myc-mobile/src/auth/AuthProvider.tsx": ("Sesión interna móvil", "Restaura, refresca y limpia tokens internos y ofrece fetch autenticado con reintento único ante 401.", "SecureStore, auth.service y React Context", "Rutas técnicas y OT LAB", "Crítico"),
        "myc-mobile/src/storage/secure-storage.ts": ("Custodia de tokens móvil", "Guarda access/refresh token en SecureStore y elimina sesiones inválidas o cerradas.", "expo-secure-store", "AuthProvider", "Crítico"),
        "docs/architecture/LAB_WORK_ORDERS.md": ("Contrato OT LAB", "Documenta aislamiento, grupo, firma única, folios, API, PDF, exportación y retiro controlado.", "Código y pruebas LAB", "Desarrollo, operación, auditoría y retiro", "Alto"),
        "docs/closures/LAB_WORK_ORDERS_VERTICAL_SLICE_2026-08-13.md": ("Cierre técnico OT LAB", "Registra alcance, evidencia, límites preservados y aceptación física pendiente.", "Contrato, implementación y validaciones LAB", "Dirección, QA y operación móvil", "Alto"),
    }
    if value in lab_files:
        return lab_files[value]

    capability_reconciliation_files = {
        "backend/app/core/permissions.py": (
            "Matriz ejecutable de permisos",
            "Declara el bootstrap interno y asigna la baja lógica de incertidumbre de certificados de patrón sólo a Calidad/Desarrollador, preservando Administrador por comodín.",
            "Roles internos, catálogo funcional y nombres de capacidades",
            "Guard API, routers, autenticación, frontend y administración",
            "Crítico",
        ),
        "backend/app/core/portal/constants.py": (
            "Catálogo de Portal",
            "Declara `portal.read` como capacidad base institucional y las capacidades específicas del Portal sin conservar `portal.view` como clave asignable.",
            "Enums y contratos de identidad del Portal",
            "Seguridad, bootstrap y frontend del Portal",
            "Crítico",
        ),
        "backend/app/core/portal/security.py": (
            "Autenticación y ownership del Portal",
            "Autentica contexto externo, deriva membresía/cliente y normaliza la clave persistida legacy `portal.view` hacia `portal.read` antes de autorizar y emitir permisos.",
            "JWT, membresías, roles/permisos y login_policy",
            "Routers `/portal` y `/client-portal`",
            "Crítico",
        ),
        "backend/app/services/portal/permission_service.py": (
            "Bootstrap conciliado del Portal",
            "Siembra `portal.read`, migra idempotentemente asignaciones legacy, desactiva `portal.view` y conserva roles personalizados sin ampliar facultades.",
            "Modelos de permisos/roles Portal y PortalPermissionCode",
            "Lifespan FastAPI, administración y pruebas Portal",
            "Crítico",
        ),
        "backend/app/routers/reference_standard_certificates.py": (
            "API de certificados de patrón",
            "Expone lifecycle y CRUD delegado; la baja lógica de incertidumbre exige explícitamente `reference_standard_certificates.delete` y propaga actor.",
            "FastAPI, schemas, servicio de certificados de patrón y permisos",
            "Calidad, Patrones y clientes API internos",
            "Crítico",
        ),
        "backend/app/security/api_access.py": (
            "Política transversal de acceso",
            "Clasifica 357 operaciones deny-by-default; usa `portal.read` con ownership y alinea delete de incertidumbre de certificado de patrón con el bootstrap catalogado.",
            "FastAPI, auth, catálogo de permisos e inventario CSV",
            "Middleware, arranque, generador y pruebas de conformidad",
            "Crítico",
        ),
        "backend/tests/test_capability_gate_reconciliation.py": (
            "Suite de conciliación TD-027",
            "Prueba baseline 19/0, cobertura completa bootstrap, sustitución Portal y asignación de delete sólo a roles autorizados.",
            "Validador, catálogo, inventario, permisos y política API",
            "Gate backend de seguridad institucional",
            "Crítico",
        ),
        "backend/tests/test_client_portal_integration.py": (
            "Suite integral del Portal",
            "Verifica registro, vínculo, login, ownership, `portal.read` y migración idempotente de roles persistidos desde `portal.view` sin pérdida de acceso.",
            "TestClient, SQLite, identidad, membresías y bootstrap Portal",
            "Regresión de Portal y seguridad",
            "Crítico",
        ),
        "frontend/src/portal/ClientPortalLayout.jsx": (
            "Layout y navegación del Portal",
            "Renderiza navegación responsive filtrada por permisos efectivos y usa `portal.read` como capacidad institucional de entrada.",
            "lucide-react, routing y permisos del perfil",
            "ClientPortalApp y usuarios externos",
            "Alto",
        ),
        "frontend/src/portal/portalCapability.test.js": (
            "Prueba de capability Portal",
            "Impide reintroducir `portal.view` en la navegación y exige la capacidad institucional `portal.read`.",
            "Node test y ClientPortalLayout",
            "Gate frontend TD-027",
            "Alto",
        ),
        "scripts/validate_capability_catalog.py": (
            "Validador institucional de capacidades",
            "Contrasta catálogo técnico, bootstrap e inventario y fija el baseline conciliado 141/62/79 y 72 permisos HTTP con brechas 19/0.",
            "Catálogo Institucional, permissions.py e inventario API",
            "Arquitectura, seguridad, revisiones y CI futura",
            "Crítico",
        ),
        "docs/closures/TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md": (
            "Cierre técnico TD-027",
            "Documenta matriz 20/2, clasificación A–H, correcciones Portal/delete, baseline 19/0, regresión y decisiones institucionales bloqueantes.",
            "Catálogo Funcional, snapshot 2B, código, inventario y pruebas",
            "Dirección, seguridad, arquitectura, QA y auditoría",
            "Alto",
        ),
    }
    if value in capability_reconciliation_files:
        return capability_reconciliation_files[value]

    # Contratos P0 cuya responsabilidad material debe prevalecer sobre cierres
    # históricos que también clasifican estos archivos compartidos.
    if value == "backend/app/services/certificates.py":
        return (
            "Lifecycle de certificados",
            "Gestiona creación, revisión y liberación; no autentica ni conserva un flujo paralelo de autenticación. Toda mutación humana exige actor y la creación derivada admite actor técnico opcional.",
            "Equipos, snapshots, auditoría, Facturación e institutional_folios",
            "ETS, Calidad, Certificados y descargas",
            "Crítico",
        )
    if value == "frontend/src/pages/ServiceOrdersPage.jsx":
        return (
            "Expediente integral ETS",
            "Orquesta ETS y proyecta Captura, Calidad, estado autenticado, descarga, Facturación y liberación sin ofrecer ni ejecutar autenticación de certificados.",
            "Componentes ETS, EtsBillingTab y APIs operativas",
            "Usuarios operativos y administrativos del expediente",
            "Alto",
        )

    sales_exception_files = {
        "backend/app/core/folios.py": (
            "Compatibilidad de folios",
            "Conserva las funciones públicas de folios y delega el formato compacto de certificados al contrato institucional vigente.",
            "Fechas, prefijos institucionales y servicios de certificados",
            "Servicios legacy que aún importan helpers de folios",
            "Alto",
        ),
        "backend/app/core/permissions.py": (
            "Matriz ejecutable de permisos",
            "Declara roles y permisos de todos los dominios; alinea CRUD de catálogo/clientes/equipos/ETS, motores y configuración institucional con el guard transversal y capacidades frontend.",
            "Servicio de autenticación y nombres de permisos",
            "Guard API, routers, capabilities, frontend y administración",
            "Crítico",
        ),
        "backend/app/main.py": (
            "Entrada FastAPI",
            "Crea la aplicación, registra routers con el guard deny-by-default, valida conformidad al arrancar y controla documentación/portal técnico por entorno.",
            "Configuración, routers, seguridad API, Facturama y servicios de arranque",
            "Uvicorn, operación y consumidores HTTP",
            "Crítico",
        ),
        "backend/app/models/__init__.py": (
            "Registro de metadata ORM",
            "Importa modelos del ERP, Motor y expediente de excepción de servicio para metadata completa.",
            "Modelos ORM del ERP y Motor",
            "Alembic, sesiones y pruebas de esquema",
            "Crítico",
        ),
        "backend/app/models/quotation_service_change.py": (
            "Expediente de desbloqueo de Ventas",
            "Persiste solicitud, folios visibles, revisión base, decisión segregada, vigencia, consumo, delta, evidencia de virginidad y resultado de reconstrucción sin exponer IDs.",
            "SQLAlchemy, cotización, ETS, catálogo, usuarios y snapshots",
            "Servicio propietario, Alembic, auditoría y pruebas",
            "Crítico",
        ),
        "backend/app/models/linked_company.py": (
            "Empresa institucional vinculada",
            "Persiste el catálogo controlado de laboratorios o empresas vinculadas y su prefijo normalizado para certificados.",
            "SQLAlchemy, catálogo y migraciones",
            "Catálogo, snapshots operativos y certificados",
            "Crítico",
        ),
        "backend/app/models/folio_sequence.py": (
            "Contador institucional anual",
            "Persiste el siguiente consecutivo por tipo documental, prefijo y año con unicidad y piso seguro.",
            "SQLAlchemy, PostgreSQL y migraciones",
            "Asignador central de certificados y órdenes de trabajo",
            "Crítico",
        ),
        "backend/app/models/catalog_item.py": (
            "Clasificación comercial del catálogo",
            "Modela composición y tipo formal acreditado, trazable o vinculado, con empresa y prefijo institucional cuando corresponde.",
            "SQLAlchemy, ServiceType y LinkedCompany",
            "Catálogo, Cotizaciones, ETS y certificados",
            "Crítico",
        ),
        "backend/app/models/service_order.py": (
            "Agregado ETS y snapshots",
            "Conserva snapshot fuente/partidas, OT, firmas y relación histórica con solicitudes persistentes de excepción.",
            "SQLAlchemy, cotizaciones, partidas, órdenes de trabajo y excepciones ETS",
            "Servicios ETS, equipos, certificados, Facturación y auditoría",
            "Crítico",
        ),
        "backend/app/models/equipment.py": (
            "Snapshot operativo de equipo",
            "Congela tipo formal de servicio, empresa vinculada y prefijo de certificado heredados desde la partida ETS.",
            "SQLAlchemy, ETS y catálogo",
            "Equipos, Calidad y emisión de certificados",
            "Crítico",
        ),
        "backend/app/schemas/service_type.py": (
            "Contrato formal de tipo de servicio",
            "Define accredited, traceable y linked, normaliza alias, valida prefijos y mapea exclusivamente al calibration_scope canónico.",
            "Pydantic y contrato de acreditación",
            "Schemas de catálogo, servicios operativos y migraciones",
            "Crítico",
        ),
        "backend/app/schemas/quotation_service_change.py": (
            "Contratos de desbloqueo de Ventas",
            "Valida solicitud, decisión, lista completa de partidas, vista previa del delta y aplicación final por folios visibles.",
            "Pydantic",
            "Router contextual y frontend de Ventas",
            "Alto",
        ),
        "backend/app/services/quotation_service_changes.py": (
            "Dominio de desbloqueo controlado",
            "Solicita, autoautoriza sólo con autoridad explícita, revisa, previsualiza y consume atómicamente una nueva revisión; revalida locks, congela historial, elimina el ETS virgen y lo recrea con el mismo OSMYC.",
            "Cotizaciones, ETS, catálogo, permisos, reconstrucción, Actividad y notificaciones",
            "Router contextual, Ventas y pruebas",
            "Crítico",
        ),
        "backend/app/services/service_order_rebuilds.py": (
            "Validador de virginidad ETS",
            "Comprueba de forma exhaustiva que no existan equipos, capturas, firmas, certificados, facturas, resoluciones ni órdenes de trabajo avanzadas antes de reconstruir.",
            "Modelos ETS, Facturación, Calidad, Certificados y Resoluciones",
            "Desbloqueo controlado y pruebas de integridad",
            "Crítico",
        ),
        "backend/app/services/quotation_revision_diff.py": (
            "Delta de revisión comercial",
            "Normaliza partidas y calcula adiciones, eliminaciones y cambios entre la revisión aprobada y la propuesta sin depender de IDs visibles.",
            "Snapshots de cotización y Decimal",
            "Vista previa y evidencia del desbloqueo",
            "Alto",
        ),
        "backend/app/services/institutional_folios.py": (
            "Asignador institucional de folios",
            "Reserva consecutivos anuales con advisory lock y row lock, respeta pisos iniciales y construye folios compactos por prefijo.",
            "PostgreSQL, FolioSequence y fechas",
            "Certificados, órdenes de trabajo y pruebas",
            "Crítico",
        ),
        "backend/app/services/certificates.py": (
            "Lifecycle y emisión de certificados",
            "Gestiona estados, carga, autenticación y liberación; toda mutación humana exige actor y sólo la creación derivada conserva actor técnico opcional. Mantiene folio anual/prefijo congelado MYCA, MYCT o vinculado.",
            "Equipos, snapshots, autenticación, auditoría, Facturación e institutional_folios",
            "ETS, Calidad, Certificados y descargas",
            "Crítico",
        ),
        "backend/app/services/folio_engine.py": (
            "Folio de orden de trabajo",
            "Delega la asignación anual de OT al contador institucional central y preserva la interfaz consumida por ETS.",
            "institutional_folios y sesión SQLAlchemy",
            "Creación y reconstrucción de ETS",
            "Crítico",
        ),
        "backend/app/routers/quotation_service_changes.py": (
            "API contextual de excepciones de Ventas",
            "Expone elegibilidad, solicitud, revisión, vista previa y aplicación por folios visibles sin pedir IDs técnicos al usuario.",
            "FastAPI, auth, schemas y servicio propietario",
            "Frontend de Cotizaciones",
            "Crítico",
        ),
        "backend/app/services/quotations.py": (
            "Dominio de cotizaciones",
            "Gestiona CRUD, estados, partidas, importes y snapshots; devuelve la revisión creada para vincular cambios excepcionales.",
            "SQLAlchemy, catálogo, Actividad y auditoría",
            "Router, PDFs, ETS y excepción contextual",
            "Crítico",
        ),
        "backend/migrations/versions/9d0e1f2a3b4c_quotation_service_change_exception.py": (
            "Migración de excepción de servicio",
            "Crea el expediente persistente, relaciones restrictivas, unicidad activa, vigencia, snapshots e índices del flujo contextual.",
            "Alembic, PostgreSQL y head 8c9d0e1f2a3b",
            "Despliegue, rollback, servicios y pruebas",
            "Crítico",
        ),
        "backend/tests/test_quotation_service_change_exception.py": (
            "Suite de desbloqueo y folios",
            "Prueba segregación, autoautorización administrativa auditada, delta, rollback, reconstrucción con mismo OSMYC, bloqueos, snapshots y secuencias 2026/2027.",
            "Pytest, SQLAlchemy, Ventas, ETS y certificados",
            "Gate backend del desbloqueo controlado",
            "Crítico",
        ),
        "frontend/src/components/sales/QuotationServiceExceptions.jsx": (
            "UI contextual de desbloqueo",
            "Desbloquea con un clic y sin modal para Administrador; conserva solicitud/revisión para menor autoridad y habilita edición sin IDs técnicos.",
            "React, cliente API y utilidades de permisos",
            "QuotationsPage y usuarios Comercial/Administrador",
            "Crítico",
        ),
        "frontend/src/components/sales/quotation-service-exceptions.css": (
            "Estilos de excepción de Ventas",
            "Define tarjeta contextual y diálogo de solicitud responsive, con foco accesible y variantes clara/oscura para perfiles sin ejecución directa.",
            "CSS y variables visuales del ERP",
            "QuotationServiceExceptions",
            "Alto",
        ),
        "frontend/src/components/service-order-exceptions.css": (
            "Estilos de excepciones ETS",
            "Aísla y normaliza el diálogo obligatorio de solicitud ETS, con diseño responsive y modo oscuro.",
            "CSS y variables visuales del ERP",
            "ServiceOrdersPage",
            "Alto",
        ),
        "frontend/src/pages/ServiceOrdersPage.jsx": (
            "Expediente integral",
            "Orquesta ETS y Captura→Calidad→Autenticación→Pago→Liberación; toda excepción operativa crea una solicitud y nunca implica ejecución directa desde la UI.",
            "Componentes ETS, EtsBillingTab, APIs operativas y etiqueta de solicitud",
            "Usuarios operativos y administrativos del expediente",
            "Alto",
        ),
        "frontend/src/utils/exceptionAuthority.js": (
            "Etiqueta segura de excepción ETS",
            "Expone únicamente la acción Solicitar excepción para evitar que la UI represente una solicitud como ejecución.",
            "JavaScript puro",
            "Superficie ETS de excepciones",
            "Alto",
        ),
        "frontend/src/utils/exceptionAuthority.test.js": (
            "Prueba de etiqueta ETS",
            "Verifica que ninguna autoridad reciba una etiqueta que implique ejecución directa desde la solicitud.",
            "Node test y utilidad de etiqueta",
            "Gate frontend de excepciones",
            "Alto",
        ),
        "frontend/src/utils/quotationServiceExceptions.js": (
            "Presentación de excepción de Ventas",
            "Deriva visibilidad, autoridad explícita, decisión de no abrir modal administrativo, etiquetas formales y validación condicional sin mostrar IDs técnicos.",
            "JavaScript puro",
            "Componentes de Ventas y pruebas frontend",
            "Alto",
        ),
        "frontend/src/utils/quotationServiceExceptions.test.js": (
            "Pruebas frontend de excepción",
            "Verifica acción contextual, ausencia de modal administrativo, permisos, etiquetas acreditado/trazable/vinculado y validación de empresa/prefijo.",
            "Node test y utilidades de Ventas",
            "Gate frontend de la excepción contextual",
            "Alto",
        ),
        "frontend/src/pages/QuotationsPage.jsx": (
            "Módulo de Cotizaciones con permisos",
            "Compone listado, detalle y catálogo; condiciona alta, edición, cambios de estado, generación ETS y administración de catálogo según permisos efectivos.",
            "React, API, accessControl, formularios, PDF, Actividad y componentes de Ventas",
            "Usuarios de Ventas con capacidades backend",
            "Crítico",
        ),
        "frontend/src/services/api.js": (
            "Cliente API compartido",
            "Centraliza transporte bearer, traduce 401/403/red, evita llamadas Dashboard sin permiso y reutiliza descargas autenticadas con manejo uniforme.",
            "fetch/HTTP, tokens y endpoints FastAPI",
            "Páginas y controladores frontend",
            "Crítico",
        ),
        "docs/architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md": (
            "Contrato canónico de desbloqueo",
            "Define elegibilidad, permisos, segregación, edición directa, delta, transacción, reconstrucción física, mismo folio visible y bloqueos operativos.",
            "Ventas, Cotizaciones, ETS, auditoría y pruebas",
            "Arquitectura, desarrollo, operación y QA",
            "Crítico",
        ),
        "docs/architecture/services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md": (
            "Contrato de clasificación de servicio",
            "Define los tres tipos formales, su relación con calibration_scope y la administración de empresas/prefijos vinculados.",
            "Catálogo, acreditación, ETS, equipos y certificados",
            "Ventas, Operaciones, Calidad y mantenedores",
            "Crítico",
        ),
        "docs/architecture/folios/CERTIFICATE_AND_WORK_ORDER_FOLIOS.md": (
            "Contrato institucional de folios",
            "Define formato compacto, prefijos, año, contador anual, pisos 2026 y concurrencia para certificados y OT.",
            "FolioSequence, PostgreSQL, certificados y ETS",
            "Operación, desarrollo, auditoría y restauraciones",
            "Crítico",
        ),
        "docs/closures/SALES_UNLOCK_AND_SERVICE_TYPES_2026-07-29.md": (
            "Cierre de desbloqueo y clasificación",
            "Consolida alcance entregado, migraciones, validaciones, pruebas, límites y pendientes verificables de la implementación.",
            "Contratos canónicos, código, migraciones y suites",
            "Dirección, desarrollo, QA y auditoría",
            "Alto",
        ),
        "docs/architecture/sales/QUOTATION_CHANGE_SERVICE_EXCEPTION.md": (
            "Contrato de excepción de servicio",
            "Define alcance, folios visibles, estados, permisos, capacidad, invariantes, atomicidad, Actividad y límites del primer caso de Ventas.",
            "Código, reglas y pruebas de Ventas",
            "Arquitectura, operación, desarrollo y QA",
            "Crítico",
        ),
        "docs/closures/QUOTATION_CHANGE_SERVICE_EXCEPTION.md": (
            "Cierre técnico de excepción de servicio",
            "Consolida diagnóstico, modelo, validaciones, pruebas, migración, archivos, límites y deuda pendiente.",
            "Contrato, implementación, migración y suites",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
    }
    if value in sales_exception_files:
        return sales_exception_files[value]

    phase_12_files = {
        "backend/app/core/config.py": (
            "Configuración central",
            "Define entorno, seguridad, storage, conversión y organización; impide producción con secreto JWT ausente, conocido, corto o de baja entropía y controla docs/portal técnico por entorno.",
            "Pydantic Settings y variables de entorno",
            "Main, servicios, workers y adaptadores del ERP",
            "Crítico",
        ),
        "backend/app/core/permissions.py": (
            "Matriz ejecutable de permisos",
            "Declara roles y permisos del ERP, incluidos lectura, operación, auditoría e infraestructura del Centro de Resoluciones.",
            "Servicio de autenticación y nombres de permisos",
            "Routers, capabilities y administración",
            "Crítico",
        ),
        "backend/app/resolution_center/__init__.py": (
            "Paquete del Centro de Resoluciones",
            "Delimita la superficie interna de la consola sin exportar infraestructura como contrato público.",
            "Adaptadores del Centro",
            "Composición backend y pruebas",
            "Alto",
        ),
        "backend/app/resolution_center/actor.py": (
            "Adaptador de actor ERP",
            "Convierte usuario y permisos ERP en ActorContext canónico con autoridad durable por operación independiente del token HTTP.",
            "Usuarios, auth y dominio de seguridad",
            "Workflow y worker indirecto",
            "Crítico",
        ),
        "backend/app/resolution_center/definitions.py": (
            "Registro institucional del Centro",
            "Vincula definición canónica, metadata versionada, esquema cerrado, presentación, fábrica de solicitud e hidratación de snapshots sin ramas por dominio.",
            "Registry del Motor e integraciones registradas",
            "Workflow, API de definiciones y frontend dinámico",
            "Crítico",
        ),
        "backend/app/resolution_center/query.py": (
            "Proyección operativa",
            "Compone lista keyset, indicadores, expediente completo y timeline con aislamiento organizacional, ownership y redacción técnica sin ser fuente de verdad.",
            "Persistencia canónica, usuarios y cursor c1",
            "API interna y frontend",
            "Crítico",
        ),
        "backend/app/resolution_center/schemas.py": (
            "Contratos internos v1",
            "Define DTOs estrictos de definiciones, lista, expediente, timeline, capabilities y comandos guiados.",
            "Pydantic",
            "Router, workflow, query y frontend HTTP",
            "Alto",
        ),
        "backend/app/resolution_center/workflow.py": (
            "Workflow administrativo",
            "Compone Registry, Lifecycle, Orchestrator, Security y dispatcher para el flujo guiado sin duplicar reglas de dominio.",
            "Servicios canónicos e integración Certificados",
            "Router interno y pruebas end-to-end",
            "Crítico",
        ),
        "backend/app/resolution_center/worker.py": (
            "Proceso worker del Centro",
            "Compone handlers de todas las integraciones registradas, reconstruye comandos durables y delega al ResolutionExecutor con heartbeats, recovery, fencing y apagado drenado.",
            "Registro institucional y runtime distribuido",
            "Operación multinodo",
            "Crítico",
        ),
        "backend/app/routers/resolution_center.py": (
            "API interna del Centro v1",
            "Aplica permisos, valida HTTP y delega lista, expediente y etapas al query/workflow sin importar infraestructura del Motor.",
            "FastAPI, schemas, auth y servicios del Centro",
            "Frontend del ERP",
            "Crítico",
        ),
        "backend/migrations/versions/d2f4a6b8c0e3_phase_12_plan_lifecycle_guard.py": (
            "Migración correctiva de Fase 12",
            "Permite transiciones canónicas del plan conservando identidad, contenido, activación e invalidación protegidos y downgrade reversible.",
            "Alembic, PostgreSQL y Fase 11",
            "Despliegues y validación de esquema",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_12_resolution_center.py": (
            "Suite específica de Fase 12",
            "Prueba flujo guiado, aislamiento, cursor, redacción, idempotencia, despacho único, actor durable y límites arquitectónicos.",
            "Centro, Motor, SQLite y migración",
            "Gate técnico de Fase 12",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_13_resolution_center_consolidation.py": (
            "Suite específica de Fase 13",
            "Prueba registro institucional, metadata, indicadores, expediente, permisos, sesión independiente y Certificados end-to-end por worker canónico.",
            "Centro, Motor, Certificados, runtime y SQLite",
            "Gate técnico de Fase 13",
            "Crítico",
        ),
        "frontend/src/constants/navigation.js": (
            "Navegación principal con capacidades",
            "Declara rutas, módulos y permisos backend necesarios para mostrar cada acceso sin convertir la UI en autoridad.",
            "Iconos, rutas y catálogo de permisos",
            "AppLayout, Dashboard y selector de módulos",
            "Alto",
        ),
        "frontend/src/pages/App.jsx": (
            "Raíz de aplicación protegida",
            "Gestiona sesión/enrutamiento, elimina el bypass de labs, bloquea navegación directa sin capacidad y entrega permisos efectivos a cada superficie.",
            "AppLayout, AccessDenied, accessControl, autenticación y páginas",
            "main.jsx y usuarios autenticados",
            "Crítico",
        ),
        "frontend/src/pages/ResolutionCenterPage.jsx": (
            "Consola de Resoluciones",
            "Implementa encabezado institucional, indicadores, formularios por metadata, expediente completo, acciones por capability y polling visible sin estado paralelo.",
            "API interna, utilidades y sistema visual",
            "Usuarios operativos, administradores y auditores",
            "Crítico",
        ),
        "frontend/src/pages/resolution-center.css": (
            "Estilos del Centro",
            "Integra tabla, filtros, badges, modales, timeline y estados responsive con variables visuales del ERP.",
            "CSS global y markup del Centro",
            "ResolutionCenterPage",
            "Alto",
        ),
        "frontend/src/services/api.js": (
            "Cliente API compartido",
            "Centraliza transporte ERP e incorpora contratos internos versionados del Centro sin acceder al Motor directamente.",
            "fetch/HTTP y endpoints FastAPI",
            "Páginas y controladores frontend",
            "Crítico",
        ),
        "frontend/src/utils/resolutionCenter.js": (
            "Reglas de presentación del Centro",
            "Deriva campos/parámetros desde esquemas versionados, convierte tipos simples o nullable, controla polling visible y habilita etapas desde contratos backend.",
            "JavaScript puro",
            "ResolutionCenterPage y pruebas",
            "Alto",
        ),
        "frontend/src/utils/resolutionCenter.test.js": (
            "Pruebas frontend del Centro",
            "Verifica formularios declarativos y campos nullable, descarte de parámetros arbitrarios, suspensión de polling y permisos por etapa.",
            "Node test y utilidades del Centro",
            "Gates frontend de Fases 12 y 14",
            "Alto",
        ),
        "docs/architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md": (
            "Contrato del Centro de Resoluciones",
            "Documenta apertura, fronteras, flujo, sesión independiente, lectura, permisos, UI, migración y límites de Fase 12.",
            "Aprobación, implementación y pruebas",
            "Arquitectura, operación, desarrollo, QA y auditoría",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_12.md": (
            "Cierre técnico de Fase 12",
            "Consolida entrega, invariantes, migración, validaciones, exclusiones y estado EN REVISIÓN.",
            "Contrato, código, suites e inventario",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
        "docs/architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md": (
            "Contrato de consolidación del Centro",
            "Define registro universal, formularios dinámicos, indicadores, expediente, integración end-to-end, permisos y límites de Fase 13.",
            "Aprobación de Fase 12, código y pruebas",
            "Arquitectura, operación, desarrollo, QA y auditoría",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_13.md": (
            "Cierre técnico de Fase 13",
            "Consolida entrega, patrón universal, integración Certificados, permisos, validaciones y estado EN REVISIÓN.",
            "Contrato, código, suites e inventario",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
    }
    if value in phase_12_files:
        return phase_12_files[value]

    phase_11_files = {
        "backend/app/resolution_engine/__init__.py": (
            "Superficie interna del Motor",
            "Publica las capacidades internas aprobadas hasta Fase 11, incluidos dispatcher, worker, recovery y handlers hacia ejecutores canónicos.",
            "Aplicación, contratos y dominio del Motor",
            "Composición interna e integraciones registradas",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/__init__.py": (
            "API de aplicación",
            "Exporta servicios canónicos y coordinación distribuida aprobados hasta Fase 11 sin transporte público.",
            "Servicios de aplicación del Motor",
            "Composición interna y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/__init__.py": (
            "API de contratos",
            "Publica comandos, puertos de ejecución y contratos de trabajo/nodo/lease distribuidos sin infraestructura.",
            "Protocols y comandos del Motor",
            "Aplicación, adaptadores y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/__init__.py": (
            "API de dominio",
            "Publica tipos puros de resolución, compensación, auditoría, seguridad y distribución determinista hasta Fase 11.",
            "Módulos puros del dominio",
            "Aplicación, infraestructura y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/exceptions.py": (
            "Errores del Motor",
            "Mantiene jerarquía estable de errores e incorpora conflictos, pérdida de lease, nodo, handler, retry seguro e incertidumbre distribuida.",
            "Python estándar",
            "Todas las capas internas y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/__init__.py": (
            "API de infraestructura",
            "Exporta adaptadores SQL y runtime, incluido el store distribuido durable de Fase 11.",
            "Persistencia, runtime y stores del Motor",
            "Composición interna y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/__init__.py": (
            "Registro ORM del Motor",
            "Publica el modelo persistente completo, incluidos nodos, trabajos y eventos distribuidos.",
            "Modelos ORM de Fases 2–11",
            "Metadata, Alembic, stores y pruebas",
            "Crítico",
        ),
        "backend/app/models/__init__.py": (
            "Registro de metadata ORM",
            "Importa modelos del ERP y las 31 entidades del Motor, incluidos consumidores, nodos, trabajos y eventos, para metadata completa.",
            "Modelos ORM del ERP y Motor",
            "Alembic, sesiones y pruebas de esquema",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_architecture.py": (
            "Pruebas arquitectónicas del Motor",
            "Verifica dirección de capas, aislamiento de fases previas, ausencia de dependencias prohibidas y propiedad de mutaciones hasta Fase 11.",
            "AST y árbol de paquetes del Motor",
            "Gate transversal de arquitectura",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_persistence_schema.py": (
            "Pruebas del esquema del Motor",
            "Verifica registro de las 31 tablas generales, FKs restrictivas, genericidad, inmutabilidad y constraints estructurales.",
            "SQLAlchemy metadata y modelos del Motor",
            "Gate transversal de persistencia",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/README.MD": (
            "Entrada normativa del Motor",
            "Ordena documentos 01–29 y publica Fases 0–11 aprobadas, Fase 12 en revisión y Fase 13 no iniciada.",
            "Roadmap, matriz, aperturas, contratos y cierres",
            "Todo participante del Motor de Resoluciones",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/distribution.py": (
            "Dominio de distribución",
            "Define tipos, estados, solicitudes, resultados, snapshots y política de retry exponencial determinista sin dependencias de infraestructura.",
            "Canonical hashing, errores y tipos estándar",
            "Dispatcher, workers, store SQL y pruebas de Fase 11",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/distribution.py": (
            "Puertos de distribución",
            "Declara registro de nodos, leases, handlers y operaciones durables de despacho, recuperación y observabilidad.",
            "Dominio distribuido y Protocol",
            "Aplicación, infraestructura SQL y composición interna",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/distribution.py": (
            "Dispatcher y workers distribuidos",
            "Coordina enqueue, claim, heartbeats de nodo/trabajo, invocación de handlers, retry seguro, drenado y recovery sin interpretar negocio.",
            "Contratos distribuidos, Clock e IdentifierFactory",
            "Supervisores internos y pruebas de Fase 11",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/distribution.py": (
            "Store SQL distribuido",
            "Implementa cola pull con SKIP LOCKED, capacidad, exclusividad por resolución, leases cercados, recuperación, retry y snapshot operacional transaccionales.",
            "SQLAlchemy, modelos y hashing canónico",
            "Dispatcher, workers, recovery y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/distribution.py": (
            "Modelo ORM distribuido",
            "Modela nodos, trabajos durables y eventos append-only con estados, constraints, hashes, índices, leases y vínculos al expediente.",
            "SQLAlchemy Base y tipos persistentes del Motor",
            "Store SQL, Alembic, metadata y auditoría operativa",
            "Crítico",
        ),
        "backend/migrations/versions/c1e3f5a7b9d2_phase_11_distributed_runtime.py": (
            "Migración de Fase 11",
            "Crea y revierte nodos, trabajos y eventos distribuidos con constraints, FKs, índices de coordinación y trigger append-only.",
            "Alembic, PostgreSQL y head aprobado de Fase 10",
            "Despliegue, respaldo, workers y validación de esquema",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_11_distributed_runtime.py": (
            "Suite específica de Fase 11",
            "Prueba idempotencia, colisiones, multinodo, exclusividad, fencing, recovery, incertidumbre, retry exacto, eventos y migración reversible.",
            "Motor, SQLAlchemy, SQLite y migración Fase 11",
            "Gate técnico de Fase 11",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/27_PHASE_11_OPENING.md": (
            "Apertura oficial de Fase 11",
            "Registra aprobación de Fase 10, alcance distribuido, invariantes, exclusiones y gate sin habilitar Fase 12.",
            "Dictamen Fase 10, roadmap y matriz",
            "Arquitectura, desarrollo, QA y revisión",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md": (
            "Contrato del runtime distribuido",
            "Documenta frontera, persistencia, claim, balanceo, fencing, recovery, retries, observabilidad, operación y límites de Fase 11.",
            "Apertura, código, migración y pruebas de Fase 11",
            "Arquitectura, operación, desarrollo, QA y auditoría",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_11.md": (
            "Cierre técnico de Fase 11",
            "Consolida la entrega distribuida aprobada, persistencia, garantías, pruebas y exclusiones.",
            "Contrato, implementación, migración y suites",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
    }
    if value in phase_11_files:
        return phase_11_files[value]

    phase_10_files = {
        "backend/app/main.py": (
            "Entrada FastAPI",
            "Crea la aplicación, registra routers y middleware, incluida la API pública y la consola interna de Resoluciones, sin incorporar negocio.",
            "Configuración, routers, Facturama y adaptadores públicos",
            "Uvicorn, operación y consumidores HTTP",
            "Crítico",
        ),
        "backend/app/models/__init__.py": (
            "Registro de metadata ORM",
            "Importa modelos operativos, entidades del Motor y consumidores API para una metadata completa de SQLAlchemy/Alembic.",
            "Modelos ORM del ERP, Motor y frontera pública",
            "Alembic, sesiones y pruebas de esquema",
            "Crítico",
        ),
        "backend/app/models/resolution_api_consumer.py": (
            "Consumidores públicos del Motor",
            "Persiste clave, hash de secreto, organización, permisos, vigencia y revocación sin guardar credenciales planas.",
            "SQLAlchemy, tipos portables y metadata ORM",
            "Autenticación API v1 y Alembic",
            "Crítico",
        ),
        "backend/app/resolution_public_api/application.py": (
            "Fachada pública v1",
            "Traduce DTOs hacia Lifecycle y auditoría, aplica idempotencia namespaced, aislamiento, filtros y keyset con identidad completa sin duplicar negocio.",
            "Servicios canónicos, seguridad integral y contratos v1",
            "Router público y pruebas contractuales",
            "Crítico",
        ),
        "backend/app/resolution_public_api/cursor.py": (
            "Codec de cursor público c1",
            "Cifra y autentica con AES-GCM versión, consumidor, organización, filtros, orden, dirección, tamaño y posición keyset sin revelar IDs internos.",
            "Cryptography, hashing canónico y secreto institucional",
            "Fachada pública, SDK indirecto y pruebas de cursor",
            "Crítico",
        ),
        "backend/app/resolution_public_api/security.py": (
            "Seguridad de consumidores v1",
            "Autentica secreto hasheado, fija organización y construye ActorContext con permisos y correlación exactos.",
            "Consumer ORM, configuración y dominio de seguridad",
            "Dependencia HTTP, fachada y provisionamiento",
            "Crítico",
        ),
        "backend/app/resolution_public_api/errors.py": (
            "Errores públicos estables",
            "Define códigos, categorías, mensajes seguros, correlación y detalles controlados independientes de excepciones internas.",
            "Contrato de transporte v1",
            "Router, handlers y SDK",
            "Alto",
        ),
        "backend/app/resolution_public_api/__init__.py": (
            "API interna de composición pública",
            "Expone la fachada y contexto de consumidor sin publicar infraestructura del Motor.",
            "Aplicación y seguridad pública",
            "Router y composición",
            "Alto",
        ),
        "backend/app/routers/resolution_public_api.py": (
            "Transporte HTTP público v1",
            "Valida headers y parámetros, publica endpoints/portal técnico y delega íntegramente en la fachada pública.",
            "FastAPI, contratos y fachada",
            "Consumidores HTTP, OpenAPI y SDK",
            "Crítico",
        ),
        "backend/myc_resolution_contracts/v1.py": (
            "Contratos públicos v1",
            "Declara DTOs estrictos, congelados y versionados de solicitudes, recursos, colecciones, capacidades y errores sin importar app.",
            "Pydantic",
            "API, SDK e integradores",
            "Crítico",
        ),
        "backend/myc_resolution_contracts/__init__.py": (
            "Paquete de contratos públicos",
            "Publica la superficie estable del contrato v1.",
            "Contratos v1",
            "SDK e integradores",
            "Alto",
        ),
        "backend/myc_resolution_sdk/client.py": (
            "SDK oficial del Motor",
            "Consume exclusivamente la API HTTP v1 y materializa DTOs públicos sin acceder a servicios, ORM o gateways.",
            "httpx y contratos públicos",
            "Aplicaciones consumidoras",
            "Crítico",
        ),
        "backend/myc_resolution_sdk/errors.py": (
            "Errores del SDK",
            "Mapea respuestas públicas fallidas a una excepción estable con código, estado y correlación.",
            "Contrato de errores HTTP",
            "Clientes del SDK",
            "Alto",
        ),
        "backend/myc_resolution_sdk/__init__.py": (
            "Paquete SDK público",
            "Publica cliente y error oficiales sin filtrar implementación interna.",
            "Cliente y errores del SDK",
            "Aplicaciones consumidoras",
            "Alto",
        ),
        "backend/migrations/versions/a0d2f4b6c8e1_phase_10_public_api_consumers.py": (
            "Migración de consumidores API",
            "Crea y revierte tabla, unicidad e índices de consumidores institucionales de Fase 10.",
            "Alembic, PostgreSQL y Fase 9",
            "Despliegue, seguridad y respaldo",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_10_public_api.py": (
            "Suite específica de Fase 10",
            "Prueba contratos, seguridad, replay, aislamiento, SDK y cursores opacos ligados a filtro/consumidor/organización/orden/versión con keyset determinista.",
            "FastAPI, SQLite, contratos, SDK y Motor",
            "Gate técnico de Fase 10",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/26_PUBLIC_API_SDK.md": (
            "Contrato API/SDK v1",
            "Documenta superficie, DTOs, seguridad, idempotencia, cursor c1 opaco ligado a consulta, SDK, compatibilidad y límites.",
            "Apertura, código, migración y pruebas de Fase 10",
            "Arquitectura, integradores, QA y seguridad",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_10.md": (
            "Cierre técnico de Fase 10",
            "Consolida implementación, persistencia, validaciones, garantías, corrección de cursor y aprobación formal en dd9a84e.",
            "Contrato, código, suites y respaldo",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
    }
    if value in phase_10_files:
        return phase_10_files[value]

    phase_9_files = {
        "backend/app/models/certificate_resolution_operation.py": (
            "Evidencia propietaria de Certificados",
            "Modela operaciones append-only, intención idempotente, snapshots y vínculo compensatorio del primer vertical de Fase 9.",
            "SQLAlchemy, Certificate y tipos JSON portables",
            "Servicio canónico, Alembic y auditoría",
            "Crítico",
        ),
        "backend/app/resolution_integrations/__init__.py": (
            "Frontera de integraciones del Motor",
            "Declara el paquete anti-corrupción para casos ERP sin incorporar dependencias propietarias al núcleo.",
            "Motor de Resoluciones y dominios propietarios",
            "Composición interna de verticales",
            "Alto",
        ),
        "backend/app/resolution_integrations/certificates/__init__.py": (
            "API interna del vertical Certificados",
            "Expone contratos y fábrica de integración sin transporte público ni lógica dentro del núcleo.",
            "Dominio, aplicación e infraestructura del vertical",
            "Bootstrap interno y pruebas",
            "Alto",
        ),
        "backend/app/resolution_integrations/certificates/domain.py": (
            "Dominio del vertical Certificados",
            "Define DTOs inmutables de solicitud, hechos, análisis, plan, simulación, revalidación y resultado con hashes canónicos.",
            "Serialización canónica del Motor",
            "Componentes puros y adaptadores",
            "Crítico",
        ),
        "backend/app/resolution_integrations/certificates/contracts.py": (
            "Puertos del vertical Certificados",
            "Declara provider read-only, comando propietario y consulta de operación fuente sin SQLAlchemy, FastAPI ni servicios concretos.",
            "DTOs del vertical y Protocol",
            "Aplicación, infraestructura y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_integrations/certificates/application.py": (
            "Definición vertical de Certificados",
            "Registra versión 1.0 y siete componentes deterministas de contexto a revalidación para resolver una liberación incorrecta.",
            "Registry, definición del Motor y puertos del vertical",
            "Orquestador, composición interna y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_integrations/certificates/infrastructure.py": (
            "Adaptadores internos de Certificados",
            "Implementa provider SQL read-only, gateways y recuperación exacta del ganador cuando una carrera de unicidad confirma primero.",
            "SQLAlchemy, runners del Motor y servicio propietario",
            "Executor, CompensationRunner y pruebas",
            "Crítico",
        ),
        "backend/app/services/certificate_resolution_operations.py": (
            "Servicio canónico de resolución de Certificados",
            "Resuelve replay histórico exacto, bloquea/revalida claves nuevas y retira/restaura visibilidad con snapshot pos-flush, auditoría y evidencia atómicas.",
            "Certificate, CertificateResolutionOperation y auditoría",
            "Domain Gateways de Fase 9",
            "Crítico",
        ),
        "backend/migrations/versions/f9c1d3e5a7b9_phase_9_certificates_integration.py": (
            "Migración de Fase 9 Certificados",
            "Crea tabla, constraints, índices y trigger append-only de operaciones propietarias mediante upgrade/downgrade reversibles.",
            "Alembic, Fase 8 y esquema de Certificados",
            "Despliegue, respaldo y auditoría",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_9_certificates.py": (
            "Suite de Fase 9 Certificados",
            "Valida componentes, replay tras deriva/inactividad, colisiones y carreras concurrentes, snapshot confirmado, rollback, seguridad, compensación y arquitectura.",
            "Motor, vertical, servicio canónico y SQLAlchemy",
            "Gate técnico del primer vertical",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md": (
            "Contrato del vertical Certificados",
            "Documenta ownership, provider, gateways, replay histórico/concurrente, snapshot pos-flush, compensación, seguridad y gate de revisión.",
            "Apertura de Fase 9, código y pruebas",
            "Arquitectura, desarrollo, QA y revisión",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md": (
            "Cierre aprobado del vertical Certificados",
            "Consolida entrega, correcciones de replay/snapshot, garantías, validaciones, commits oficiales y aprobación de Fase 9.",
            "Contrato, implementación y validaciones de Fase 9",
            "Arquitectura, dirección, QA y auditoría",
            "Alto",
        ),
        "docs/architecture/resolution-engine/README.MD": (
            "Entrada normativa del Motor",
            "Ordena documentos 01–26, publica Fases 0–9 aprobadas y Fase 10 en revisión con la corrección del cursor opaco implementada.",
            "Roadmap, matriz, aperturas, contratos y cierres",
            "Todo participante del Motor de Resoluciones",
            "Crítico",
        ),
        "docs/modules/calidad/AUTENTICACION_CERTIFICADOS.md": (
            "Contrato vigente de Certificados",
            "Define aprobación, autenticación, liberación y resolución extraordinaria con replay histórico y snapshot confirmado sin reescribir evidencia.",
            "Calidad, servicios canónicos, Motor y almacenamiento",
            "Operación, backend, frontend, QA y auditoría",
            "Alto",
        ),
        "docs/architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md": (
            "Contrato de persistencia del Motor",
            "Documenta esquema general, evidencia append-only de Certificados y protocolo transaccional de unicidad, lock, replay y snapshot pos-flush.",
            "Modelos ORM, repositorio y migraciones Fases 2–9",
            "Motor, integraciones, Alembic, QA y auditoría",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/25_PHASE_10_OPENING.md": (
            "Apertura oficial de Fase 10",
            "Autoriza contratos públicos versionados, API institucional, SDK y documentación, preservando seguridad e impidiendo distribución o IA.",
            "Aprobación de Fase 9, roadmap y matriz",
            "Arquitectura, desarrollo, QA, seguridad y revisión",
            "Crítico",
        ),
    }
    if value in phase_9_files:
        return phase_9_files[value]

    phase_8_files = {
        "backend/app/resolution_engine/__init__.py": (
            "API interna estable del Motor",
            "Expone Lifecycle, ejecución, compensación y comando de outbox autorizados hasta Fase 8 sin incorporar transporte ni ERP.",
            "Aplicación, contratos y dominio del Motor",
            "Bootstrap futuro e integraciones registradas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/__init__.py": (
            "API de aplicación",
            "Publica catálogo/evaluador integral, Lifecycle, ejecución, compensación, auditoría y outbox protegidos hasta Fase 8.",
            "Servicios de aplicación del Motor",
            "Composición interna y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/__init__.py": (
            "API de contratos",
            "Expone comandos y puertos protegidos de Lifecycle, ejecución, compensación, auditoría y outbox sin filtrar infraestructura.",
            "Protocols y comandos del Motor",
            "Aplicación, adaptadores y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/audit.py": (
            "Contratos de auditoría protegida",
            "Declara AuditQuery con ActorContext, instante, operación, contexto y concesión reusable_read exactos, además de puertos read-only.",
            "Dominio de auditoría y seguridad",
            "AuditQueryService, adaptador SQL y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/execution.py": (
            "Contratos de ejecución protegida",
            "Declara comandos con operación/decisión exactas, verificación pre-replay y reserva única de publicación outbox por organización.",
            "ActorContext, dominio de ejecución y Lifecycle",
            "Executor, stores, publicador y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/execution.py": (
            "Executor protegido",
            "Valida actor/comando, exige seguridad antes del replay y coordina Lifecycle, idempotencia, locks, handlers y checkpoints.",
            "ExecutionStore, Engine, ActionRunner y state machine",
            "Composición interna y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/outbox.py": (
            "Publicación outbox protegida",
            "Verifica la decisión institucional antes de leer y publica explícitamente el lote autorizado sin scheduler ni retry.",
            "PublishOutboxCommand, OutboxStore, Publisher y Clock",
            "Composición operativa futura y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/audit.py": (
            "Adaptador SQL de auditoría",
            "Verifica actor/contexto exactos y materializa el expediente read-only dentro de un snapshot estable.",
            "Verificador integral, SQLAlchemy, Repository y Projector",
            "AuditQueryService y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/compensation.py": (
            "Adaptador SQL de compensación",
            "Revalida la misma evidencia integral en preparación/inicio y persiste planes/checkpoints con Lifecycle, locks, auditoría y outbox.",
            "SQLAlchemy, verificador integral y modelos del Motor",
            "Planner, Executor y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/execution.py": (
            "Adaptador SQL de ejecución",
            "Verifica autorización antes de replay y dentro de la reserva, vinculando ejecución con plan, revalidación y decisión exactos.",
            "SQLAlchemy, verificador integral, Lifecycle y controles",
            "ResolutionExecutor y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/lifecycle.py": (
            "Persistencia protegida de Lifecycle",
            "Verifica creación/transición exactas, conserva sus IDs de decisión y aplica únicamente transiciones calculadas por la máquina.",
            "SQLAlchemy, verificador integral, modelos y Repository",
            "ResolutionLifecycleService, executors y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/outbox.py": (
            "Store de outbox protegido",
            "Consume una autorización, congela IDs de un único lote organizacional y devuelve su resultado en replay sin seleccionar otro lote.",
            "SQLAlchemy, verificador integral y modelos outbox",
            "OutboxPublicationService y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/security.py": (
            "Evidencia y recursos de seguridad",
            "Persiste decisiones con base canónica/revalidación y comprueba raíces, planes, simulaciones, revalidaciones y ejecuciones exactas.",
            "SQLAlchemy, dominio de seguridad y modelos del Motor",
            "AuthorizationService, verificador común y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/evidence.py": (
            "Modelo ORM de evidencia integral",
            "Define decisiones con modo/intención canónica, consumos append-only únicos y reserva de lote, además de evidencia/outbox previos.",
            "SQLAlchemy Base y modelos del Motor",
            "Seguridad, auditoría, Alembic y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/persistence/execution.py": (
            "Modelo ORM de ejecución protegida",
            "Vincula cada ejecución nueva con plan, revalidación y decisión de seguridad exactos y conserva checkpoints/resultados.",
            "SQLAlchemy Base y modelos de evidencia",
            "ExecutionStore, Repository, Alembic y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/application/security.py": (
            "Autorización integral",
            "Mantiene el único evaluador de políticas e incorpora el catálogo versionado de acción, permiso, recurso y riesgo con deny-by-default.",
            "Dominio de seguridad, Clock y puertos de evidencia",
            "Lifecycle, ejecución, compensación, auditoría, outbox y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/lifecycle.py": (
            "Contratos protegidos de Lifecycle",
            "Declara creación con decisión exacta y el puerto que verifica seguridad antes de reconstruir o transitar la raíz.",
            "ActorContext, definiciones y dominio Lifecycle",
            "Servicio, adaptador SQL y pruebas de Fases 4 y 8",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/security.py": (
            "Dominio de seguridad integral",
            "Modela identidad, autenticación, permisos contextuales, recursos exactos, catálogo de controles y decisiones canónicas inmutables.",
            "Canonical hashing y value objects",
            "Evaluador, verificadores, persistencia y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/security_decisions.py": (
            "Verificador de decisiones persistidas",
            "Comprueba modo, operación e intención exactos y reserva consumos single-operation transaccionales sin reevaluar políticas.",
            "SQLAlchemy, modelos del Motor y dominio de seguridad",
            "Lifecycle, ejecución, compensación, auditoría y outbox",
            "Crítico",
        ),
        "backend/migrations/versions/e7f9a1b3c5d7_resolution_engine_phase_8_security.py": (
            "Migración de Fase 8",
            "Vincula decisiones con revalidación y ejecuciones con autorización exacta mediante columnas compatibles, FKs, constraint e índice reversibles.",
            "Alembic, Fase 6 y modelos de seguridad/ejecución",
            "Despliegues, restauraciones y auditoría del Motor",
            "Crítico",
        ),
        "backend/migrations/versions/f8a0b2c4d6e8_phase_8_security_decision_replay.py": (
            "Corrección de replay de Fase 8",
            "Agrega semántica e intención canónica, consumo append-only único y reserva exacta de lote outbox mediante una migración reversible.",
            "Alembic, head de Actividad y modelos de seguridad/outbox",
            "Despliegues, restauraciones, Motor y auditoría",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_phase_8_security.py": (
            "Suite de seguridad integral",
            "Cubre catálogo, tampering, replay de creación, versión Lifecycle, concurrencia, rollback, migraciones y verificador único.",
            "Dominio, aplicación, adaptadores SQL y migración de Fase 8",
            "Gate específico de Fase 8",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/21_PHASE_8_OPENING.md": (
            "Apertura oficial de Fase 8",
            "Registra autorización, alcance, exclusiones, dependencias, invariantes, validaciones y cumplimiento de la restricción previa a Fase 9.",
            "Aprobación de Fase 7, roadmap y matriz",
            "Arquitectura, dirección, desarrollo y revisión",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/22_INTEGRAL_SECURITY.md": (
            "Contrato de seguridad integral",
            "Documenta autoridad única, catálogo, reglas reforzadas y protección de Lifecycle, ejecución, compensación, auditoría y outbox.",
            "Fases 1 a 7, código, migración y suite de Fase 8",
            "Arquitectura, desarrollo, QA y fases posteriores",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_8.md": (
            "Cierre aprobado de Fase 8",
            "Consolida componentes, invariantes, migración, validaciones, commits, exclusiones y aprobación formal que habilita Fase 9.",
            "Implementación, arquitectura y validaciones de Fase 8",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
        "docs/architecture/resolution-engine/23_PHASE_9_OPENING.md": (
            "Apertura oficial de Fase 9",
            "Registra autorización, integración gradual, ownership, contratos, exclusiones, invariantes y gates por caso vertical.",
            "Aprobación de Fase 8, roadmap y matriz",
            "Arquitectura, dirección, desarrollo, QA y revisión",
            "Crítico",
        ),
    }
    if value in phase_8_files:
        return phase_8_files[value]

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

    phase_7_files = {
        "backend/app/resolution_engine/application/__init__.py": (
            "API de aplicación",
            "Publica servicios aprobados de seguridad integral, Lifecycle, ejecución, compensación, outbox y consultas de auditoría hasta Fase 8.",
            "Servicios de aplicación del Motor",
            "Composición backend futura y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/application/audit.py": (
            "Consultas de auditoría",
            "Autoriza y construye reportes, timelines y consultas de evidencia sin mutar el expediente.",
            "AuditRecordStore, AuditAccessVerifier y AuditEngine",
            "Composición interna futura y pruebas de Fase 7",
            "Crítico",
        ),
        "backend/app/resolution_engine/contracts/__init__.py": (
            "API de contratos",
            "Expone puertos de runtime, seguridad, Lifecycle, ejecución, compensación y auditoría sin filtrar infraestructura.",
            "Protocols y comandos del Motor",
            "Aplicación, adaptadores y definiciones",
            "Alto",
        ),
        "backend/app/resolution_engine/contracts/audit.py": (
            "Contratos de auditoría",
            "Declara AuditQuery y puertos read-only de expediente consistente y autorización sin filtrar ORM o transporte.",
            "Dominio puro de auditoría y Protocol",
            "Aplicación, adaptadores y pruebas de Fase 7",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/audit.py": (
            "Dominio de auditoría y evidencia",
            "Modela nodos, vínculos, registro, timeline y reporte; verifica hashes, alcance, secuencia y correlaciones con diagnósticos estables.",
            "Canonical hashing y errores del Motor",
            "Servicio de auditoría, adaptador SQL y pruebas",
            "Crítico",
        ),
        "backend/app/resolution_engine/domain/__init__.py": (
            "API de dominio",
            "Publica tipos inmutables de seguridad integral, Lifecycle, ejecución, compensación, auditoría y evidencia aprobados hasta Fase 8.",
            "Módulos puros del dominio",
            "Aplicación, contratos, adaptadores y consumidores",
            "Alto",
        ),
        "backend/app/resolution_engine/domain/exceptions.py": (
            "Jerarquía de errores",
            "Distingue errores de definición, Lifecycle, seguridad, ejecución, compensación y auditoría con códigos y contexto estables.",
            "Excepciones estándar",
            "Todas las capas del Motor y mapeo API futuro",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/__init__.py": (
            "API de infraestructura",
            "Publica runtime, repositorios, verificador integral y adaptadores SQL de Lifecycle, ejecución, compensación, outbox y auditoría hasta Fase 8.",
            "Infraestructura del Motor",
            "Bootstrap futuro y pruebas",
            "Alto",
        ),
        "backend/app/resolution_engine/infrastructure/audit.py": (
            "Adaptador SQL de auditoría",
            "Valida actor, contexto y decisión integral exactos y materializa el expediente read-only dentro de un snapshot REPEATABLE READ/SERIALIZABLE sin modificar Lifecycle.",
            "SQLAlchemy, ResolutionRepository, AuditProjector y contratos",
            "AuditQueryService y pruebas persistentes",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/audit_projection.py": (
            "Proyector SQL de evidencia",
            "Traduce explícitamente las 26 tablas generales a nodos y vínculos puros agrupados por planificación, gobierno, ejecución, seguridad y compensación.",
            "SQLAlchemy inspection, ResolutionRecord y dominio de auditoría",
            "SqlAlchemyAuditRecordStore y pruebas persistentes",
            "Crítico",
        ),
        "backend/app/resolution_engine/infrastructure/security.py": (
            "Persistencia de evidencia de seguridad",
            "Conserva decisiones append-only, revalidación exacta y base canónica completa dentro del context_snapshot para verificación integral.",
            "SQLAlchemy, dominio de seguridad y modelos generales",
            "Autorización, auditoría y pruebas",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_audit.py": (
            "Pruebas de dominio de auditoría",
            "Cubre hashes, replay, timeline, filtros, huecos, duplicados, evidencia ajena, referencias y acceso denegado.",
            "AuditEngine, AuditQueryService y pytest",
            "Gate funcional de Fase 7",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_audit_persistence.py": (
            "Pruebas persistentes de auditoría",
            "Reconstruye Lifecycle, seguridad, ejecución y compensación; intercala una transición concurrente y verifica snapshot íntegro, autorización integral y ausencia de efectos.",
            "SQLAlchemy, servicios y expediente completo del Motor",
            "Gate de integración de Fase 7",
            "Crítico",
        ),
        "backend/tests/resolution_engine/test_architecture.py": (
            "Pruebas de arquitectura",
            "Inspecciona capas, autoridad de Lifecycle, verificador único, frontera de snapshot y ausencia de ERP, transporte, workers o fases posteriores.",
            "ast, pathlib y paquete resolution_engine",
            "Gates arquitectónicos de Fases 1 a 8",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/19_PHASE_7_OPENING.md": (
            "Apertura aprobada de Fase 7",
            "Registra autorización, objetivo, alcance, exclusiones, entregables, invariantes y gate de Auditoría y Evidencia.",
            "Roadmap, matriz y capacidades aprobadas de Fases 1 a 6",
            "Arquitectura, dirección, desarrollo y revisión de Fase 7",
            "Crítico",
        ),
        "docs/architecture/resolution-engine/20_AUDIT_EVIDENCE.md": (
            "Contrato de Auditoría y Evidencia",
            "Documenta modelo, autorización, reconstrucción, hashes, timeline, persistencia reutilizada, invariantes y límites de Fase 7.",
            "Especificación, matriz y código de Fase 7",
            "Arquitectura, desarrollo, QA y fases posteriores",
            "Crítico",
        ),
        "docs/closures/RESOLUTION_ENGINE_PHASE_7.md": (
            "Cierre técnico de Fase 7",
            "Registra componentes, integridad, autorización, pruebas, ausencia de migración y aprobación formal mediante los commits aceptados.",
            "Implementación, arquitectura y validaciones de Fase 7",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
    }
    if value in phase_7_files:
        return phase_7_files[value]

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
            "Modela efectos activos, plan, pasos, reserva y resultado; valida clausura transitiva antes de invertir orden/dependencias y consolidar.",
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
            "Distingue errores de definición, Lifecycle, seguridad, ejecución y compensación, incluida clausura con paso/dependientes/rutas estables.",
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
            "Reconstruye efectos confirmados activos excluyendo compensaciones exitosas, revalida autorización y persiste planes/checkpoints con Lifecycle, locks, auditoría y outbox.",
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
            "Expone las 27 entidades ORM vigentes, incluido el consumo append-only de decisiones y las cuatro estructuras compensatorias.",
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
            "SQLAlchemy Session y modelos persistentes del expediente",
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
            "Verifica clausura directa/transitiva A→B→C, error estructurado, orden inverso, efectos activos, estrategias, resúmenes e invariantes.",
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
            "Verifica clausura A→B→C antes de persistir, efectos no confirmados/ya compensados, replay, autorización, vínculos, locks, auditoría y outbox sobre SQL.",
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
            "Verifica 27 tablas, consumo único de decisiones, relaciones, aislamiento, inmutabilidad, outbox y compensación.",
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
            "Registra componentes, invariantes, corrección de clausura, validaciones, migración y aprobación final mediante los dos commits aceptados.",
            "Implementación, arquitectura y validaciones de Fase 6",
            "Arquitectura, desarrollo, QA, dirección y auditoría",
            "Alto",
        ),
        "docs/architecture/resolution-engine/19_PHASE_7_OPENING.md": (
            "Apertura propuesta de Fase 7",
            "Define nombre, objetivo, alcance, exclusiones, entregables, invariantes, consistencia y gate de Auditoría y Evidencia sin autorizar implementación.",
            "Roadmap, matriz y capacidades aprobadas de Fases 1 a 6",
            "Arquitectura, dirección, desarrollo y revisión previa a Fase 7",
            "Crítico",
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

    certificate_authentication_files = {
        "backend/app/routers/certificates.py": (
            "Router HTTP de Certificados",
            "Expone la única operación HTTP de autenticación como adapter delgado de Calidad, exige permiso y propaga actor sin poseer negocio ni transacción.",
            "FastAPI, permisos y certificate_authentication.py",
            "QualityPage y clientes API autorizados",
            "Crítico",
        ),
        "backend/app/services/certificate_authentication.py": (
            "Autoridad de autenticación documental",
            "Bloquea el certificado, valida actor y origen Calidad, genera/versiona el PDF autenticado y confirma estado, auditoría y evento idempotente en una sola transacción.",
            "Certificate, Master XLSX, storage, LibreOffice, auditoría y Activity",
            "Router de Certificados y pruebas de integridad",
            "Crítico",
        ),
        "backend/app/services/certificates.py": (
            "Lifecycle de certificados",
            "Gestiona creación, revisión y liberación; no autentica ni conserva un flujo paralelo de autenticación. Toda mutación humana exige actor y la creación derivada admite actor técnico opcional.",
            "Equipos, snapshots, auditoría, Facturación e institutional_folios",
            "ETS, Calidad, Certificados y descargas",
            "Crítico",
        ),
        "backend/tests/test_certificate_authentication_integrity.py": (
            "Suite de autoridad de autenticación",
            "Protege adapter delgado, ausencia de ruta ETS, actor/origen, lock, audit/evento, commit único y rechazo idempotente de una segunda autenticación.",
            "Pytest, FastAPI, SQLAlchemy y servicios de Certificados",
            "Gate backend del P0 de autenticación",
            "Crítico",
        ),
        "frontend/src/pages/ServiceOrdersPage.jsx": (
            "Expediente integral ETS",
            "Orquesta ETS y proyecta Captura, Calidad, estado autenticado, descarga, Facturación y liberación sin ofrecer ni ejecutar autenticación de certificados.",
            "Componentes ETS, EtsBillingTab y APIs operativas",
            "Usuarios operativos y administrativos del expediente",
            "Alto",
        ),
        "frontend/src/pages/certificateAuthenticationAuthority.test.js": (
            "Prueba de superficie canónica",
            "Impide reintroducir acciones de autenticación en ETS o un cliente masivo y confirma que Calidad conserva la única acción frontend.",
            "Node test, QualityPage, ServiceOrdersPage y api.js",
            "Gate frontend del P0 de autenticación",
            "Alto",
        ),
        "docs/closures/CERTIFICATE_AUTHENTICATION_INTEGRITY_SPRINT_2026-08-10.md": (
            "Cierre P0 de autenticación",
            "Consolida superficies, divergencias, autoridad, lifecycle, concurrencia, actor, auditoría, eventos, Motor, regresión, capability gate y deuda restante.",
            "Código, pruebas y documentación canónica de Certificados",
            "Revisión técnica, QA, operación y auditoría",
            "Alto",
        ),
    }
    if value in certificate_authentication_files:
        return certificate_authentication_files[value]

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
    if value == "backend/app/schemas/service_order.py":
        return ("Contrato Pydantic operacional", "Valida ETS y el lifecycle solicitado/autorizado/ejecutado de excepciones, propagando ServiceScope con claves canónicas.", "service_scope.py, Pydantic y modelos ORM", "Router/servicio ETS y cadena Catálogo→ETS→Certificado", "Alto")
    if value in {"backend/app/schemas/quotation.py", "backend/app/schemas/equipment.py"}:
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
    if value == "backend/app/services/service_orders.py":
        return ("Autoridad única ETS", "Implementa creación, actualización, OT/firmas, estados, baja y lifecycle de excepciones; exige actor en toda mutación crítica y permite que el mismo Administrador recorra tres etapas auditables sin efectos antes de ejecutar.", "Modelos ETS/Invoice, schemas, folios, auditoría y Activity", "Router ETS, equipos, certificados, Facturación y pruebas", "Crítico")
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
        "Fecha de inventario: 2026-07-29.",
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
