> Estado: **TD-027 — BLOQUEADO POR DECISIÓN**
>
> Corte: 2026-08-11
>
> Alcance: conciliación del capability gate, sin ampliar el Catálogo Institucional Funcional 1.0

# Cierre técnico — TD-027 Conciliación del capability gate

## Resultado ejecutivo

El gate reproducible queda **VERDE**. Se corrigieron las dos divergencias
accionables: `portal.view` se sustituyó por la capacidad institucional existente
`portal.read`, y `reference_standard_certificates.delete` se incorporó al
bootstrap con asignación mínima a Calidad y Desarrollador, además del comodín de
Administrador. El inventario conserva 357 operaciones y ya no utiliza permisos
ausentes del bootstrap.

Permanecen 19 diferencias literales entre permisos HTTP de compatibilidad y el
snapshot técnico de permisos granulares propuestos. No son drift: eran el
baseline conocido de Etapa 2B y el Catálogo Funcional aprobado confirma varios
como actuales o de compatibilidad. Los casos que requieren separar autoridades
críticas no se migraron automáticamente. Por ello el gate está verde como
detector de cambios no conciliados, pero TD-027 queda **BLOQUEADO POR DECISIÓN**.

## 1–4. Matriz de las 20 divergencias originales

`Catálogo` distingue el snapshot técnico 2B de la autoridad funcional 1.0.
`Sí/No` en Inventario y Bootstrap describe el estado anterior al sprint.

| Capability | Endpoint/uso | Inventario | Catálogo | Bootstrap | Snapshot | Origen | Clasificación | Diagnóstico y acción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `certificates.capture` | 6 operaciones PATCH/draft/generate/send/start/validate | Sí | Técnico: no literal; funcional M21.A03/A05: actual, por reconciliar | Sí | Brecha conocida | Captura/Certificados | H | Agrupa crear, actualizar, retorno y envío; no dividir sin decisión. Se conserva. |
| `certificates.match_override` | aceptación manual de coincidencia | Sí | Técnico propone `certificates.match.override`; funcional M21.A04 aprueba la clave actual | Sí | Brecha conocida | Captura | G | Diferencia de nomenclatura del snapshot no autoritativo. Se conserva la clave aprobada actual. |
| `certificates.quality` | 5 acciones de revisión, rechazo, corrección, retorno y suspensión | Sí | Técnico propone varias claves; funcional M22.A02: actual, requiere conciliación | Sí | Brecha conocida | Calidad | H | Separar revisión/retorno/suspensión cambia autoridades N3. Requiere decisión. |
| `certificates.upload_pdf` | carga PDF y dos cargas ETS | Sí | Técnico propone tres familias; funcional M21.A03/M23.A02 reconoce la actual | Sí | Brecha conocida | Captura/ETS | H | Una sustitución única sería semánticamente incorrecta; conservar hasta decidir por superficie. |
| `integrations.facturama.status` | estado de Facturama | Sí | Técnico propone `integrations.read`; funcional M37.A01 reconoce la actual | Sí | Brecha conocida | Integraciones | G | Compatibilidad funcional explícita; no requiere cambio automático. |
| `invoices.manage` | 11 mutaciones fiscales/configuración | Sí | Técnico propone siete claves; funcional M34.A02–A04/M35.A06 la marca compatible | Sí | Brecha conocida | Facturación | H | Mezcla N3/N4; separar emisión, conciliación, notas y ajustes exige decisión fiscal/RBAC. |
| `metrology.execute` | cálculo y perfiles | Sí | Técnico propone read/review; funcional M31.A01 aprueba `metrology.execute` | Sí | Brecha conocida | Metrología | G | El permiso actual representa la capacidad funcional aprobada. |
| `operational_engines.execute` | 8 consultas/ejecuciones | Sí | Técnico propone create/read; funcional M31.A02: compatibilidad y futuras manage/test | Sí | Brecha conocida | Motores operativos | H | La granularización altera quién configura, prueba y ejecuta. No se infiere. |
| `pattern_selection.execute` | candidatos, sugerencia y validación | Sí | Técnico propone create; funcional M32.A01 aprueba execute | Sí | Brecha conocida | Selección de patrones | G | La clave ejecutable actual es la autoridad funcional aprobada. |
| `payments.manage` | registrar pago | Sí | Técnico propone `invoices.payments.register`; funcional M35.A02 mantiene manage compatible | Sí | Brecha conocida | Pagos | H | Registrar/aplicar/recibo son decisiones N3 separables; requieren decisión. |
| `payments.read` | 3 consultas/recibo | Sí | Técnico propone invoices read/download; funcional M35.A01/M35.A04 aprueba payments.read | Sí | Brecha conocida | Pagos/Cartera | G | Se conserva el dominio funcional Pagos. |
| `portal.view` | 20 operaciones Portal | Sí | Técnico: no; funcional M38.A01 ya define `portal.read` | No | **Brecha nueva** | Portal posterior a Etapa 2B | D | Existía equivalente institucional. Se reemplazó por `portal.read`; alias legacy sólo normaliza permisos persistidos. |
| `quotations.exceptions.inspect` | 6 operaciones de excepción comercial | Sí | Snapshot técnico previo no la contiene; funcional M11.A07 la aprueba como actual | Sí | Posterior al snapshot | Desbloqueo controlado | E | Capacidad posterior técnicamente justificada y ya aprobada funcionalmente; se conserva sin reabrir el catálogo técnico congelado. |
| `release.manage` | 2 liberaciones de certificado y lote ETS | Sí | Técnico propone certificate/service-order específicos; funcional M14.A06/M23.A03 exige reconciliar | Sí | Brecha conocida | ETS/Certificados | H | Liberación N4 necesita decisión única sobre `release.manage` frente a `certificates.release`. |
| `sat_catalogs.manage` | 4 favoritos/alias | Sí | Técnico propone create/delete; funcional M36.A02/A03 conserva familias manage | Sí | Brecha conocida | SAT | G | El snapshot técnico no refleja las capacidades funcionales actuales de SAT. |
| `service_orders.sign` | confirmar firmas | Sí | Técnico propone `service_orders.status.confirm`; funcional M17.A02 aprueba sign | Sí | Brecha conocida | Firmas ETS | G | Confirmar ciclo de firmas no equivale a confirmar estado ETS; se conserva sign. |
| `services.manage_linked_company` | alta de empresa vinculada | Sí | Técnico propone catalog_items.create; funcional M10.A04 aprueba la capacidad específica | Sí | Brecha conocida | Catálogo MYC | G | Menor privilegio favorece conservar la capacidad específica. |
| `uncertainty_models.read` | 6 consultas | Sí | Técnico propone uncertainty.read; funcional M33.A01 aprueba la actual | Sí | Brecha conocida | Incertidumbre | G | Se conserva el límite explícito de modelos. |
| `uncertainty_models.update` | 16 mutaciones/lifecycle | Sí | Técnico propone ocho claves; funcional M33.A02/A03 conserva update y propone futuras lifecycle | Sí | Brecha conocida | Incertidumbre | H | Mezcla edición y autorizaciones N3; requiere decisión antes de dividir roles. |
| `users.manage` | 33 operaciones internas/Portal | Sí | Técnico cubre sólo seis; funcional M03.A02/A05 la declara compatibilidad y M38.A03 reserva familia Portal | Sí | Brecha conocida ampliada | Usuarios y accesos | H | Separar identidad, roles y membresías N4 requiere gobierno; no se sustituyó por inferencia. |

Resumen de clasificación primaria: **D: 1, E: 1, G: 9, H: 9**. No se
detectaron casos F. Los casos A/B/C se presentan en las correcciones concretas
porque afectan la implementación o bootstrap, no otra de las 20 claves.

## 2. Las dos divergencias inventario → bootstrap

| Capability | Endpoint/uso | Diagnóstico | Clasificación | Corrección |
| --- | --- | --- | --- | --- |
| `portal.view` | base transversal de 20 operaciones Portal | Código posterior al snapshot usó una clave inexistente pese a existir `portal.read`. | A + D | Backend, guard, roles base, autenticación, dashboard, frontend e inventario usan `portal.read`. Los registros legacy se normalizan al resolver permisos. |
| `reference_standard_certificates.delete` | DELETE de incertidumbre de certificado de patrón | La clave ya estaba en catálogo, pero faltaba en bootstrap y el router exigía update mientras el guard exigía delete. | A + C | Se declaró en `PERMISSIONS`, se asignó sólo a Calidad/Desarrollador, y router/guard quedaron alineados. |

## 3. Explicación 19/1 → 20/2

El snapshot 2B esperaba 19 permisos HTTP sin coincidencia literal y un permiso
catalogado sin bootstrap: `reference_standard_certificates.delete`.
`portal.view` apareció después con la integración del Portal y agregó
simultáneamente una brecha frente al catálogo técnico y otra frente al
bootstrap. El gate detectó correctamente el drift: 19/1 pasó a 20/2.

Después de reutilizar `portal.read` y completar el bootstrap de `.delete`, el
estado es **19/0**. El snapshot ejecutable se actualizó únicamente en los
conteos derivados: 141 permisos actuales, 62 coincidencias, 79 gaps actuales,
72 permisos del inventario, 19 gaps catálogo, 0 bootstrap y 596 futuros.

## 5–8. Correcciones y casos conocidos

- `portal.read` protege el acceso base; los permisos específicos del Portal y
  el ownership por membresía siguen aplicándose. No se concedió acceso nuevo.
- El alias `portal.view → portal.read` opera sólo al resolver permisos
  persistidos legacy; tokens y UI reciben la clave institucional.
- `reference_standard_certificates.delete` corresponde a una baja lógica de
  incertidumbre, operación N3 del dominio. Calidad y Desarrollador ya tenían
  create/update/approve; ningún rol Comercial, Técnico, Captura, Finanzas,
  Cliente, Operador o Auditor recibió delete.
- El Catálogo Institucional Funcional y el snapshot técnico congelado no fueron
  modificados.

## 9. Excepciones ETS

`requested → authorized → executed` permanece bajo `service_orders.update`.
M14.A04 define la capacidad futura desde gobierno de resoluciones, pero no
aprueba tres claves ni una equivalencia reutilizable. Solicitar es ejecución,
autorizar es N4 y ejecutar es N4; separarlas puede cambiar roles y segregación.
No se inventaron claves. El Administrador conserva `*` y puede completar sus
tres etapas, manteniendo expedientes, transiciones, audit y eventos separados.

## 10. Autenticación de Certificados

`certificates.approve` se mantiene. El catálogo funcional M22.A03 nombra
`certificates.authenticate` como capacidad nueva futura, pero no autoriza su
incorporación automática. Autenticación continúa en Calidad, mediante la
autoridad canónica `certificate_authentication.authenticate_certificate`, y
liberación sigue siendo una decisión distinta.

## Propuesta de cambios institucionales

No se aplicó ningún cambio al Catálogo Funcional 1.0.

| Capacidad posible | Módulo/acción | Naturaleza/criticidad | Alcance/roles a decidir | Alternativas | Estado |
| --- | --- | --- | --- | --- | --- |
| Familia de excepción ETS, claves por definir | M14.A04 Resolver excepciones | ejecución/autorización, N4 | por resolución; Administrador conserva autoejecución documentada; demás roles pendientes | mantener update, una capacidad gobernada o separación por etapa | REQUIERE DECISIÓN |
| `certificates.authenticate` | M22.A03 Autenticar | autorización/ejecución, N4 | Calidad y Administrador como candidatos; asignación definitiva pendiente | mantener `certificates.approve` o separar autenticación | REQUIERE DECISIÓN |
| Granularización de los nueve casos H de la matriz | Certificados, Facturación, Motores, Pagos, Liberación, Incertidumbre, Usuarios | N2–N4 | roles/scope por acción | conservar compatibilidad o migrar de forma versionada | REQUIERE DECISIÓN |

## 11–13. Gate, bootstrap, inventario y snapshot

- Bootstrap: +1 clave catalogada (`reference_standard_certificates.delete`).
- Roles internos: Calidad y Desarrollador reciben delete; Administrador lo
  satisface por `*`.
- Portal: `portal.read` sustituye `portal.view`; alias legacy sin nueva
  autoridad.
- Inventario: 357 operaciones, 72 permisos únicos, cero permisos huérfanos de
  bootstrap.
- Snapshot esperado del validador: actualizado a hechos reconciliados; no se
  alteró el catálogo congelado.
- Estado final del gate: **VERDE**, con baseline gobernado 19/0.
- Datos bootstrap locales: `portal.read` activo con seis roles base;
  `portal.view` inactivo y sin asignaciones después de migrarlas.
- Esquema: sin cambios y Alembic continúa en `e7b62b8a9421`. El respaldo
  canónico `backup_erp_myc_antes_prueba.sql` fue regenerado y verificado.

## 14. Regresión

| Validación | Resultado |
| --- | --- |
| Capability gate | verde; 19 catálogo / 0 bootstrap |
| Pruebas focales capability/API/Portal | 16 passed, 2 warnings |
| Backend completo | 471 passed, 19 subtests, 3 warnings |
| Frontend completo | 42 passed |
| Vite build | correcto; warning de chunk >500 kB |
| `compileall` | correcto |
| `pip check` | correcto; advertencia de caché no escribible |
| `scripts/myc doctor` | correcto con PostgreSQL, Alembic y LibreOffice disponibles |
| Alembic `check` | sin operaciones nuevas |
| Inventario API | 357/357; CSV idéntico a runtime |

Las advertencias son las deprecaciones preexistentes de Starlette/httpx,
Passlib/crypt y configuración Alembic. No se modificaron pruebas para ocultar
fallos.

## 15. Riesgos restantes

- Nueve familias H necesitan decisión institucional antes de granularizar.
- La fila legacy `portal.view` queda inactiva y sin asignaciones después de
  migrar roles a `portal.read`; su eliminación física futura requiere comprobar
  despliegues y respaldos, pero ya no concede autoridad.
- El bootstrap estático y la siembra implícita del Portal continúan como deuda
  independiente TD-029; este sprint no implementa RBAC administrable.
- Gate verde significa ausencia de drift contra el baseline aceptado, no que
  los 19 permisos de compatibilidad ya sean el modelo RBAC definitivo.

No se inició otro P1, funcionalidad, cambio visual ni fase del Motor.
