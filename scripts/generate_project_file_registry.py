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
}
EXCLUDED_PREFIXES = ("backend/resources/sat/reports/",)
OFFICIAL_IGNORED_RESOURCES = (Path("backend/resources/sat/catalogo sat.xlsx"),)
FORCE_RECLASSIFY = {
    "AGENTS.md",
    "docs/BACKUP_ESTADO_ACTUAL.md",
    "docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md",
    "scripts/generate_project_file_registry.py",
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

    if "/migrations/versions/" in value:
        return ("Migración Alembic", f"Aplica la revisión {subject} del esquema y conserva la evolución reproducible de PostgreSQL.", "Alembic, modelos ORM y base de datos", "Alembic durante upgrade/downgrade y despliegues", "Crítico")
    if value == "AGENTS.md":
        return ("Normas del repositorio", "Define las reglas persistentes de cierre, respaldo, inventario, reset, auditoría integral y actualización documental obligatoria en cada tarea.", "Procesos de desarrollo, auditoría y jerarquía documental", "Agentes Codex y mantenedores del ERP", "Crítico")
    if value == "docs/BACKUP_ESTADO_ACTUAL.md":
        return ("Estado operativo vigente", "Resume exclusivamente el estado verificable actual, migraciones, validaciones y pendientes operativos, con enlaces al canon especializado.", "PROJECT_STATUS, TECHNICAL_DEBT, validaciones y migraciones vigentes", "Agentes Codex, desarrollo y operación", "Alto")
    if value == "docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md":
        return ("Bitácora histórica", "Conserva íntegra la cronología de entregas, respaldos, cierres y validaciones anterior a la separación del estado operativo vigente.", "Cortes y cambios históricos del ERP", "Auditorías forenses y mantenedores", "Medio")
    if value == "scripts/generate_project_file_registry.py":
        return ("Generador de inventario", "Regenera el inventario desde rutas existentes, excluye artefactos y conserva las filas previamente auditadas para no perder la revisión humana.", "Git, árbol del repositorio y PROJECT_FILE_REGISTRY", "Agentes Codex y mantenedores", "Alto")
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
        "Fecha de inventario: 2026-07-21.",
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
