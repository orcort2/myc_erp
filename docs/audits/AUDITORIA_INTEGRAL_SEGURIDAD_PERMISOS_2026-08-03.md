# Auditoría integral de seguridad y permisos

## Resultado

**Estado:** crítico. De 306 operaciones, 181 exigen permiso explícito, 32 sólo sesión, 15 aceptan sesión opcional, 4 usan consumidor/organización y 74 son públicas o no protegidas. El frontend no filtra navegación por capacidades (`AppLayout.jsx` mapea `navigation` completa).

## Matriz ruta → permiso efectivo

La matriz agrupa operaciones con contrato idéntico. “Público” significa que el árbol FastAPI no contiene `get_current_user`, `require_permission` ni `consumer_context`; no afirma que la ruta deba ser pública.

| Recurso/acción | Endpoints | Esperado | Real backend | Roles declarados | Frontend | Hallazgo |
| --- | --- | --- | --- | --- | --- | --- |
| Salud/raíz | `GET /`, `/api/health` | Público, mínimo | Público; health estático | Todos | N/A | Sin readiness ni versión de dependencias |
| Registro/login/refresh | `/api/auth/*` | Público sólo login/bootstrap; registro controlado | Registro siempre público; refresh sin rotación | N/A | Login expone registro | Alta ilimitada de Cliente; sin rate limit |
| Sesión actual | `GET /api/auth/me` | Sesión | Sesión | Todos | Sí | Correcto en aislamiento |
| Clientes listar/leer/exportar | `GET /api/clients*` | `clients.read` + ámbito | Público | Comercial/Captura/Finanzas | Visible a todo usuario | Exposición PII y exportación global |
| Clientes crear | `POST /api/clients` | `clients.create` | Público | Comercial | Sí | Mutación anónima |
| Clientes editar/importar/constancia/perfiles | PATCH/POST/DELETE de `/api/clients` | `clients.update` | Público, salvo archive/restore/delete | Comercial | Sí | Mass assignment mitigado por Pydantic, autorización ausente |
| Clientes archive/restore/delete | rutas homónimas | `clients.update` | Permiso explícito | Comercial | Sí | Correcto; borrado físico de elegibles requiere especial revisión |
| Catálogo CRUD | `/api/catalog-items` | read/create/update/delete | Público | Roles parciales | Editor embebido | Alteración anónima de precios/servicios |
| Linked companies alta | `POST .../linked-companies` | manage linked company | Sólo sesión, sin permiso | Desarrollador/Comercial declarados | Sí | Escalamiento horizontal |
| Cotizaciones lectura/PDF/snapshots | GET `/api/quotations` | `quotations.read` + ámbito | Público | Comercial/Finanzas/Captura | Sí | Datos comerciales globales |
| Cotizaciones mutaciones/estados/items | POST/PATCH/DELETE | permisos de acción | Sesión opcional; anónimo permitido | Comercial | Sí | Flujo comercial íntegro manipulable |
| Excepción cotización | `/quotation-service-exceptions` | permisos por etapa | Sólo sesión; servicio valida permisos | Roles específicos | Sí | Mejor que CRUD general; requiere matriz HTTP 403 |
| ETS CRUD/transiciones/PDF | `/api/service-orders` | permisos granulares | Público | Técnico/Comercial/etc. declarados | Sí | Estados, firmas, PDFs y cierre anónimos |
| Firmas/excepciones ETS | `confirm-signatures`, `exceptions` | sign/exception | Sesión opcional | Técnico/roles excepción | Sí | Actor puede ser nulo; excepción legacy |
| Captura ETS | capture package/files | permisos captura | Permiso explícito | Captura | Sí | Protegido, pero carga no acotada |
| Equipos CRUD/estados | `/api/equipment` | equipment.* | Público | Técnico | Dentro de ETS | Mutación operativa anónima |
| Hojas de campo | `/api/field-sheets` | field_sheets.* | Permisos explícitos | Técnico/Calidad/Captura | Dentro ETS | Cobertura adecuada por ruta; falta ámbito por registro |
| Plantillas Hojas | `/api/field-sheet-templates` | permisos por acción | Explícitos | Calidad/Captura/Técnico | Ajustes | Correcto a nivel función |
| Certificados | `/api/certificates` | permisos por estado | Explícitos | Captura/Calidad/Finanzas | ETS/Calidad | Correcto funcional; probar IDOR por entidad |
| Portal certificados/listados | `/api/client-portal/*` | `*_own` + tenant | Público, sin cliente | Cliente | Sin UI | Crítico: listado global e IDOR PDF |
| Facturas/pagos/CxC | `/api/invoices`, `/invoice-payments` | invoices/payments | Permisos explícitos | Finanzas | Workbench/Billing | Mejor superficie general; falta ámbito organizacional |
| Configuración institucional GET | `GET /institutional-configuration` | settings.read o público acotado | Público | No aplicado | Plantillas | Expone datos institucionales, riesgo bajo aislado |
| Configuración PATCH | PATCH misma ruta | settings.manage | Usa `field_sheet_templates.update` | Calidad/Desarrollador | Panel de Hojas | Permiso semánticamente incorrecto |
| Documentos controlados | `/api/documents` | documents.* | Explícitos | Calidad/otros lectura | Control documental | Correcto por función |
| Patrones/procedimientos/perfiles/incertidumbre | routers correspondientes | permisos declarados | Explícitos | Calidad/Técnico/Desarrollador | Algunas páginas ocultas | Correcto por función; sin ámbito |
| Motores operativos legacy | `/api/operational-engines/*` | permisos técnicos | Público | No aplicado | No consumidor claro | Cálculo/preparación/folios expuestos |
| Actividad | `/api/activity/*` | sesión + permiso entidad | Sesión; servicio valida permiso y entidad | Familias activity | Panel genérico | Diseño correcto; faltan defaults BD y pruebas HTTP extensivas |
| Notifications/Communications | routers | sesión y pertenencia | Sesión; servicio filtra participante | Todos/participantes | Sí | Correcto básico; sin rate limit/paginación completa |
| Audit logs | `GET /api/audit-logs` | audit_logs.read | Explícito | Calidad/Auditor/Dev | Ajustes | Correcto; tabla no protegida append-only por DB |
| Centro Resoluciones | `/api/resolution-center/v1` | permisos por etapa | `read` en consulta + workflow granular | Operador/Calidad/etc. | Sí | Núcleo deny-by-default razonable |
| API pública Motor | `/api/public/resolution-engine/v1` | consumidor, org, permiso | `consumer_context` + seguridad Motor | Consumidores | SDK | Correcto por contrato; rotación operacional no demostrada |
| Portal desarrollador | `GET /api/developers/resolution-engine` | sesión técnica o docs públicas decididas | Público | Ninguno | No claro | Expone especificación; decisión pendiente |
| Verificación certificado | `GET /verify/{code}` | Público por código no secuencial | Público | Todos | Enlace PDF | Aceptable si código tiene entropía; rate limit no existe |

## Roles efectivos declarados

| Rol | Autoridad relevante | Problema |
| --- | --- | --- |
| Administrador | `*` | Autoautoriza excepciones; adecuado sólo con MFA/auditoría, hoy inexistente |
| Comercial | clientes/cotizaciones/actividad/equipo adicional | Backend general no fuerza la matriz |
| Técnico | equipos/hojas/patrones/ETS | Rutas de Equipos/ETS abiertas vuelven irrelevante el rol |
| Captura | captura/certificados/documentos lectura | Correcto en rutas nuevas; superficies ETS duplican acciones |
| Calidad | calidad/aprobación/documental/gobierno | Puede editar configuración institucional por permiso de plantillas |
| Finanzas | facturas/pagos/release | Superficie mejor protegida; no hay segregación para nota fiscal/cancelación |
| Cliente | permisos `*_own` | Ningún endpoint portal los aplica |
| Desarrollador | permisos técnicos amplios, no `*` | Adecuado conceptualmente; UI no filtra |
| Operador | operar resoluciones, no autorizar | Motor aplica segregación |
| Auditor | lectura/auditoría | Motor y audit logs; resto carece de vista sólo lectura coherente |

## Controles de seguridad

| Control | Estado | Evidencia/riesgo |
| --- | --- | --- |
| Password hash | Confirmado | PBKDF2-SHA256; falta política de fortaleza/rehash/comprometidas |
| JWT tipos/expiración | Confirmado | access 8 h, refresh 30 d; pruebas distinguen tipo |
| Revocación/rotación | Ausente | No jti, sesión persistente, denylist ni refresh rotation |
| Secreto | Crítico | `secret_key="change-this-secret-key"`; sin guard productivo |
| Recuperación/cambio password | Ausente | Sin endpoints/flujo |
| Último administrador | Confirmado | `services/users.py` bloquea retiro/desactivación |
| CORS | Parcial | Lista hardcodeada en `main.py`; `settings.cors_origins` no se usa |
| CSRF | No aplicable parcialmente | Bearer header, no cookie; XSS compromete tokens localStorage |
| XSS | Riesgo | No `dangerouslySetInnerHTML` encontrado; tokens persistentes amplifican cualquier XSS |
| SQL injection | Sin evidencia directa | SQLAlchemy predominante; no se encontró concatenación SQL explotable en corte |
| IDOR | Confirmado | Portal global y PDF por ID; múltiples rutas internas sin ámbito |
| Mass assignment | Mitigado parcialmente | Schemas Pydantic; autorización ausente domina riesgo |
| Path traversal | Mitigado centralmente | `resolve_storage_path` y `safe_filename`; revisar rutas que escriben fuera del helper |
| MIME/firma/tamaño | Inconsistente | Activity valida; capture ZIP/XLSX y constancias no tienen límites uniformes |
| ZIP Slip | Mitigado en captura | Usa `Path(info.filename).name`, no `extractall`; persiste ZIP bomb/memoria |
| SSRF | Sin superficie confirmada | URLs externas configuradas, no entrada libre evidente; NO VERIFICADO en todas las plantillas |
| Secretos en repo | No confirmado | Búsqueda por nombres sólo encontró `.env.example`; historial/entropía no verificados |
| Logs sensibles | Parcial | Logging escaso; Facturama registra diagnósticos, requiere redacción formal |
| Rate limiting | Ausente | Login, registro, verify, API/portal sin limitador visible |
| Auditoría append-only | Parcial | Motor sí usa triggers/evidencia; `audit_logs` general carece de trigger inmutable |
| Backups | Alto riesgo | SQL real rastreado; head desactualizado; controles de cifrado/retención no demostrados |

## Pruebas de seguridad

`backend/tests/test_auth_security.py` cubre tipos JWT y que el schema de registro rechace roles solicitados. Sólo se hallaron aserciones 401/403 adicionales en excepciones, Activity y API pública. No existe una prueba parametrizada de las 306 operaciones ni una política automatizada que falle si se agrega un endpoint interno público.

## Prioridad

1. Guard global deny-by-default y allowlist explícita de públicas.
2. Tenant de cliente obligatorio y pruebas IDOR.
3. Secreto/rotación/revocación/rate limit/reset de password.
4. Permisos por recurso y actor obligatorio en todas las mutaciones.
5. Filtrado de navegación y acciones desde capacidades backend, sin usarlo como control primario.
