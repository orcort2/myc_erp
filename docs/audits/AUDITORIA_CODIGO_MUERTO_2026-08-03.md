# Inventario de código muerto, duplicado, huérfano y artefactos

No se eliminó ningún archivo. “Candidato” exige verificación dinámica antes de retirar.

## Confirmados por referencias locales

| Ruta/elemento | Clasificación | Evidencia | Recomendación |
| --- | --- | --- | --- |
| `frontend/src/pages/NotificationCenterPage.jsx` | Archivo sin consumidor | El símbolo sólo aparece en su archivo; App enruta `/notifications` a CommunicationsPage | Retirar o reintegrar tras E2E |
| `frontend/src/components/invoice-workbench/InvoiceWorkbenchModal.jsx` | Componente paralelo no usado | Workbench consume `InvoiceWorkbenchDialog`; símbolo sin importador | Retirar tras confirmar historia; preserva deuda de modal paralelo |
| `frontend/src/pages/CapturePage.jsx` | Pantalla importada pero sin módulo navegable | App tiene rama `selectedModule.key === capture`; `modules` no define `capture` | Definir si se retira o se vuelve ruta oficial |
| `CertificatesPage.jsx`, `EquipmentPage.jsx`, `QualityPage.jsx` | Pantallas autónomas ocultas | Ramas App sin claves correspondientes; flujo vive en ETS | Consolidar decisión y eliminar duplicación futura |
| `ProceduresPage.jsx`, `UncertaintyPage.jsx`, `FlowTestPage.jsx` | Pantallas ocultas/lab | Sin entradas en `modules`/navigation | Habilitar por permiso o archivar |
| `backend/app/services/additional_equipment_resolutions.py::request_additional_equipment_resolution` | Productor sin consumidor de producción | Referencias sólo en pruebas; ningún router/UI lo invoca | Conectar desde ETS o retirar afirmación de integración de origen |
| “Lote próximamente” en `ServiceOrdersPage.jsx` | Botones placeholder | Dos botones disabled | No presentar como flujo implementado |
| Settings `ComingSoon` | Placeholder | Operación, Facturación, Integraciones y Sistema | Etiquetar alcance real; no simular configuración |

## Duplicación material

| Área | Fuentes duplicadas | Riesgo |
| --- | --- | --- |
| ETS | `routers/service_orders.py` y `services/service_orders.py` contienen máquinas/reglas | Estados divergentes y actor opcional |
| Certificados/Calidad | Autenticar en Calidad y ETS | Acción formal disponible en dos superficies |
| OT/Firmas | `service_orders.work_order_number`, `service_work_orders`, firmas legacy y ciclos | Integridad/migración/downgrade |
| Workbench UI | Dialog vigente y Modal huérfano; lab usa Header/Sidebar alternos | Regresión de controlador único |
| Identidad | configuración, template, invoice settings, assets/literales | Documentos históricos divergentes |
| CORS | `settings.cors_origins` y lista hardcodeada en `main.py` | Configuración declarada no aplicada |
| Estado frontend/backend | `constants/statuses.js` y máquinas Python | Desalineación manual posible |
| Activity/Communications | conversación institucional genérica y mensajes de Communications | Responsabilidades cercanas sin contrato unificado total |

## Artefactos incluidos o visibles

| Artefacto | Estado | Riesgo/recomendación |
| --- | --- | --- |
| `backup_erp_myc_antes_prueba.sql` (74.3 MB) | Rastreado | Datos/sensibilidad/tamaño; mover a backup cifrado y retirar de Git sólo con plan |
| `docs.zip` | Rastreado y modificado preexistente | Duplicación opaca de documentación |
| `storage/activity/invoice/1/9/app.zip` | Rastreado | Binario arbitrario dentro de evidencia; política de malware/retención |
| 55 rutas `storage/` | Rastreado | PDFs/XLSX/XML y constancias reales no deben vivir en Git |
| `backend/app.zip`, `frontend/src.zip` | No rastreados preexistentes | Copias completas, riesgo de fuga/confusión |
| `.DS_Store`, `._*`, pyc | 874 físicos fuera de dependencias | Limpiar de forma recuperable; reforzar ignore |
| `frontend/dist` | Generado local | Excluir; build reproducible |
| `backend/output`, `output`, `tmp`, `storage` | Generados/operativos | Ya excluidos del registro oficial; no versionar |
| root `BytesIO`, `from`, `import`, `io` | Rastreado | Archivos accidentales sin extensión; inspeccionar y retirar |

## Código grande y mantenibilidad

| Archivo | Líneas | Hallazgo |
| --- | ---: | --- |
| `frontend/src/styles/global.css` | 8,418 | Selectores globales, colisión y revisión visual difícil |
| `ServiceOrdersPage.jsx` | 4,598 | ETS, OT, equipo, hoja, captura, calidad, certificados, billing y modales mezclados |
| `QuotationsPage.jsx` | 3,449 | Cotización, catálogo, template, import/export y excepciones mezclados |
| `invoice-workbench.css` | 3,213 | Estilo masivo |
| `frontend/src/services/api.js` | 1,696 | 179 funciones y contratos de todos los dominios |
| `backend/app/services/clients.py` | 1,311 | CRUD, import/export, parsing, archivos y deletion graph |
| `resolution_center/workflow.py` | 1,289 | Orquestación extensa; justificada parcialmente, requiere límites |

## TODO/comentarios/configuración obsoleta

- `scripts/build.sh` usa texto “TODO OK”, no un pendiente funcional.
- Catálogo está comentado en `navigation.js` aunque el editor vive dentro de Cotizaciones.
- README conserva flujo Lead/Agenda/Llamado/Encuesta y estado Fase 13/14 obsoleto.
- `backend/.env.example` es el único archivo de código/config coincidente con nombres sensibles; no se exponen valores en esta auditoría.
- No se confirmaron imports circulares en tiempo de importación: compileall, import FastAPI y pruebas pasan. No hubo analizador estático dedicado de ciclos.

## Endpoints sin consumidor frontend confirmado

Existen 306 operaciones backend y 179 funciones exportadas en `api.js`; una comparación textual no basta por paths dinámicos. Sí se confirmaron como superficies técnicas sin consumidor UI evidente `/api/operational-engines/*`, `/api/developers/resolution-engine` y parte de métodos de reconciliación/nota de crédito. Deben conservarse hasta revisar clientes externos/SDK/logs; no se clasifican como eliminables.

## Orden de limpieza futuro

1. Separar datos/binarios/backup de Git sin borrar hasta validar custodia.
2. Marcar rutas/páginas oficiales y retirar sólo duplicados confirmados.
3. Modularizar ETS/Cotizaciones/api.js/CSS después de congelar E2E.
4. Generar reporte de reachability con ESLint/tsserver y cobertura dinámica.
5. Revisar migraciones/columnas legacy con telemetría antes de eliminar.
