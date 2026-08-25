> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para observaciones funcionales y UX abiertas
>
> Prevalece sobre: listas de observaciones en auditorías, cierres y archivos
>
> Corte verificado: 2026-08-25

# Registro de observaciones abiertas

Este registro contiene únicamente desviaciones funcionales o de UX que siguen
`pendiente` o `parcial`. La deuda de seguridad, arquitectura, mantenimiento,
operación o pruebas vive sólo en [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md). Las
resoluciones históricas se consultan en `docs/closures/`, `docs/audits/` y Git;
no se duplican aquí.

| ID | Módulo | Observación vigente | Estado | Evidencia / deuda relacionada |
| --- | --- | --- | --- | --- |
| OBS-006 | Clientes | `city` y `legal_name` conservan compatibilidad legacy que todavía se expone en el contrato vigente. | parcial | Cierre técnico Clientes; auditoría 2026-07-21 |
| OBS-007 | Contactos | Falta decidir si queda absorbido por Clientes o existe como módulo autónomo. | pendiente | `CURRENT_SCOPE.md`; auditoría 2026-07-21 |
| OBS-008 | Cotizaciones | Restaurar un snapshot no recupera sus partidas aunque el snapshot las conserva. | parcial | Auditoría 2026-07-21 |
| OBS-010 | Agenda | No existe módulo autónomo con calendario, estados, reprogramación y recordatorios; sólo fecha dentro de ETS. | pendiente | `CURRENT_SCOPE.md`; auditoría 2026-07-21 |
| OBS-011 | Llamados | No existe entidad autónoma, folio, bitácora ni captura de resultado; sólo hito dentro de ETS. | pendiente | `CURRENT_SCOPE.md`; auditoría 2026-07-21 |
| OBS-018 | Hojas de Campo | Renderer React/PDF, semántica de familias, cálculos metrológicos, aprobación propia y E2E de las 23 plantillas no están cerrados como experiencia integral. | parcial | TD-008, TD-009 y auditorías de Hojas de Campo |
| OBS-023 | Captura | El flujo XLSX y fingerprint está probado, pero falta una bandeja formal para archivos genuinamente no identificados y un E2E autenticado completo. | parcial | TD-010; auditoría Paquete de Captura |
| OBS-025 | Calidad/Certificados | Aprobación, autenticación y liberación están implementadas; falta cerrar el E2E hasta verificación pública con datos vigentes y validación visual autenticada. | parcial | Auditoría integral y cierre de autenticación |
| OBS-026 | Facturación | Borrador, pagos y CxC funcionan en el Workbench único; siguen parciales el descarte seguro, notas fiscales, ciclo CFDI productivo y experiencia de documentos/excepciones. | parcial | TD-011 y TD-012; auditorías de Facturación |
| OBS-030 | Catálogo MYC | Los endpoints están protegidos, pero no existe una experiencia oficial independiente completa fuera de sus consumidores actuales. | parcial | Auditoría integral 2026-08-03 |
| OBS-031 | Catálogos SAT | La fuente oficial XLSX está gobernada, pero las entradas internas CSV/JSON y los roles consumidores requieren cierre funcional. | parcial | Arquitectura SAT; auditoría 2026-07-21 |
| OBS-032 | Patrones/Procedimientos/Incertidumbre | Falta validar renovación, vigencia, selección y conexión extremo a extremo con Hojas de Campo; Procedimientos permanece oculto. | parcial | `PROJECT_STATUS.md`; TD-009 |
| OBS-041 | Cierre comercial | CRM/Leads, Encuestas y reporte final no tienen implementación; falta decidir su inclusión en 1.0. | pendiente | `CURRENT_SCOPE.md`; especificación histórica V2 |
| OBS-042 | Integraciones | Google Drive no existe y Facturama continúa limitado a Sandbox. | pendiente | TD-012; auditorías de Facturación |
| OBS-043 | ETS/Calidad UX | ETS conserva estados contextuales y Calidad es el único autenticador, pero falta validación visual autenticada en varios anchos y con datos representativos. | parcial | Cierre de autenticación; auditoría 2026-08-10 |
| OBS-044 | Calidad UX | Anterior/Siguiente y retorno contextual están implementados; falta E2E autenticado con certificados reales visibles en la bandeja. | parcial | Navegación consecutiva de Calidad 2026-07-21 |
| OBS-045 | Excepciones transversales | Equipo adicional usa el Motor y ETS separa solicitud/autorización/ejecución; los demás dominios requieren evaluación individual sin convertir el Motor en flujo fiscal o propietario. | parcial | Fase 14; Sprint Integridad ETS |

## Resoluciones retiradas del registro activo

Las 88 filas `OBS-R*` y las observaciones abiertas ya marcadas `resuelta`
se retiraron durante la consolidación documental del 2026-08-25. No aportaban
pendientes actuales y repetían cierres, auditorías o decisiones. Git conserva
su texto completo y los documentos de evidencia mantienen la trazabilidad
necesaria.

## Regla de cierre

Una observación se elimina de esta tabla cuando existe evidencia verificable
de resolución y, si afecta avance, se sincroniza
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). Si el pendiente es exclusivamente
técnico, se registra sólo en `TECHNICAL_DEBT.md`; no se copia aquí.
