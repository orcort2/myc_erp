> Estado: VIGENTE
>
> Tipo: Matriz normativa de implementación
>
> Autoridad: Orden técnico aprobado para implementar el Motor de Resoluciones
>
> Complementa a: `01_VISION.md` a `12_ROADMAP.md`
>
> Corte verificado: 2026-07-24

# Matriz de implementación del Motor de Resoluciones

## Propósito

Esta matriz convierte la especificación arquitectónica en una secuencia
ejecutable para el ERP MYC. Define el alcance exacto de cada fase, sus
dependencias, los bloqueadores que pueden corregirse y la evidencia requerida
antes de solicitar autorización para continuar.

No reduce el alcance normativo del Motor ni habilita implementaciones
provisionales que omitan seguridad, evidencia, idempotencia o propiedad de
dominio.

## Reglas de ejecución

1. Sólo puede existir una fase activa.
2. Una fase no puede incorporar componentes asignados a una fase posterior.
3. La deuda general del ERP no bloquea el Motor.
4. Una deuda se corrige dentro del proyecto únicamente cuando contradice una
   dependencia obligatoria de la fase vigente.
5. Toda corrección de deuda debe quedar vinculada al componente y gate que
   bloqueaba.
6. Los módulos propietarios conservan sus reglas, transacciones, folios,
   documentos y validación final.
7. El Motor sólo coordina mediante contratos y Domain Gateways.
8. Cada fase debe terminar con suite completa, validación de integración,
   documentación sincronizada y commit exclusivo.
9. Después del commit se requiere aprobación expresa para iniciar la fase
   siguiente.

## Estados de control

| Estado | Significado |
| --- | --- |
| `NO INICIADA` | La fase no puede recibir cambios de implementación. |
| `ACTIVA` | Única fase autorizada para trabajo. |
| `EN REVISIÓN` | Implementación cerrada; sólo admite correcciones derivadas de su validación. |
| `APROBADA` | Evidencia aceptada y commit de fase confirmado. |
| `BLOQUEADA` | Existe una contradicción directa que debe resolverse antes de continuar. |

## Matriz maestra

| Fase | Estado inicial | Componentes autorizados | Dependencias obligatorias | Bloqueadores corregibles en la fase | Gate de salida |
| --- | --- | --- | --- | --- | --- |
| 0. Preparación arquitectónica | `APROBADA` | Canon documental, README, matriz, gates, inventario y línea base | Especificación completa y reglas del repositorio | Especificación fuera del índice, ausencia de matriz y contradicciones de precedencia documental | Arquitectura ratificada, matriz registrada, validaciones completas y commit de Fase 0 |
| 1. Contratos y núcleo | `EN REVISIÓN` | Organización de paquetes, contratos tipados, enumeraciones, errores, hashes, reloj, identificadores, `ResolutionRegistry` y pruebas arquitectónicas | Fase 0 aprobada | Sólo dependencias o acoplamientos que impidan aislar el núcleo; no seguridad, persistencia ni gateways todavía | Definiciones registrables sin modificar el núcleo y dependencias prohibidas cubiertas por pruebas |
| 2. Persistencia completa | `NO INICIADA` | Modelos del Motor, restricciones, índices, repositorios, migraciones, inmutabilidad y outbox estructural | Contratos de Fase 1 estables; cadena Alembic coherente | Deriva o convenciones que impidan migrar exclusivamente las tablas del Motor | Ciclo reconstruible desde persistencia, upgrade/downgrade verificados y único head |
| 3. Seguridad, identidad y evidencia | `NO INICIADA` | `ActorContext`, autenticación aplicable, permisos atómicos, políticas, segregación, autorización base, auditoría append-only y protección de datos | Persistencia de Fase 2 | Registro con escalación, refresh aceptado como access, actor opcional, rutas del Motor sin deny-by-default o identidad insuficiente | Cada decisión demuestra actor, autoridad, política y evidencia inmutable |
| 4. Ciclo de decisión sin efectos | `NO INICIADA` | State machine, lifecycle, context builder, fact providers, análisis, estrategia, plan, simulación, autorización y revalidación sin mutaciones | Seguridad y evidencia de Fase 3 | Cualquier fuente viva o servicio no canónico que impida snapshots confiables de sólo lectura | Flujo completo hasta revalidación sin efectos sobre dominios |
| 5. Ejecución y recuperación | `NO INICIADA` | Saga, executor, idempotencia, concurrencia, locks, retries, reconciliación, compensación, outbox operativo y workers | Plan autorizado/revalidado de Fase 4 | Mutaciones duplicadas, servicios no canónicos, operaciones no idempotentes o ciclo de excepción que mezcle solicitud y ejecución | Caídas y respuestas inciertas recuperables sin duplicar efectos |
| 6. API institucional | `NO INICIADA` | `/api/v1/resolutions`, comandos, consultas, errores, idempotency key, ETag/versión, filtros y paginación | Servicios de aplicación de Fases 1 a 5 | Infraestructura HTTP que impida autenticación, autorización, concurrencia o errores contractuales | Contrato HTTP completo con pruebas 401/403/409/412/422/423 |
| 7. UC-001 vertical | `NO INICIADA` | `service_order.add_additional_equipment`, providers, estrategias, planes, policies, revalidator y gateways concretos | API y ejecución completas; servicios canónicos de dominios participantes | Duplicidad ETS/Facturación/Equipos, excepción ETS sin `requested/approved/executed` u operación participante no idempotente | UC-001 completo, recuperable y sin acceso directo del Motor a tablas de dominio |
| 8. Frontend operativo | `NO INICIADA` | Bandeja, detalle, timeline, simulación, autorizaciones, ejecución, recuperación y cliente API | API institucional estabilizada | Navegación o cliente API que obligue a duplicar estado, permisos o reglas del backend | UI sin segunda máquina de estados ni lógica de dominio |
| 9. Expansión UC-002 a UC-040 | `NO INICIADA` | Nuevas definiciones y componentes especializados por grupos de dominio | UC-001 aprobado y núcleo estable | Sólo contradicciones del dominio incorporado en el grupo vigente | Matriz de casos con evidencia completa, sin condicionales nuevos en el núcleo |
| 10. Operación y gobierno | `NO INICIADA` | Métricas, trazas, alertas, panel de recuperación, retención, runbooks, restauración y gobierno de definiciones/políticas | Motor funcional e integrado | Ausencia de observabilidad o recuperación verificable para operar el Motor | Operación reproducible, alertada, restaurable y gobernada |
| 11. Evolución de plataforma | `NO INICIADA` | SDK/API pública, offline completo, ejecución multinodo, alta disponibilidad e IA asistida | Motor institucional estabilizado y evidencia histórica suficiente | Contradicciones que impidan distribución, compatibilidad o explicabilidad | Capacidades evolucionadas sin alterar contratos ni reinterpretar históricos |

## Dependencias entre componentes

| Componente | Depende de | No puede depender de |
| --- | --- | --- |
| `ResolutionRegistry` | Contratos y versiones de definición | Modelos concretos de ETS, Facturación, Equipos u otros dominios |
| State machine | Catálogo controlado de estados y eventos de auditoría | Condicionales particulares de un tipo de resolución |
| Context builder | Fact providers registrados y contratos read-only | Consultas ad hoc a tablas de dominio |
| Analyzer | Snapshot persistido y definición registrada | Estado vivo no capturado |
| Strategy selector | Análisis, políticas y versiones | Lógica dispersa en routers |
| Plan builder | Estrategia, contexto, contratos de operación | Ejecución directa o generación de folios |
| Simulator | Plan exacto y gateways de simulación/read-only | Efectos, reservas, documentos o folios |
| Authorization service | Identidad, políticas, plan y simulación exactos | Booleanos mutables de aprobación |
| Revalidator | Plan autorizado y nuevo snapshot | Suposiciones basadas en el contexto anterior |
| Executor | Plan autorizado/revalidado, idempotencia y locks | Solicitud original o lógica improvisada |
| Domain Gateway | Servicio canónico del módulo propietario | ORM directo de otro dominio |
| Audit service | Actor, correlación, hashes y eventos | Registros editables o borrado operativo |
| Recovery worker | Persistencia, idempotencia y evidencia | Memoria del proceso interrumpido |

## Matriz de deuda bloqueante

La deuda se evalúa nuevamente al abrir cada fase. Esta tabla no autoriza su
corrección anticipada.

| Condición actual conocida | Primera fase que puede bloquear | Tratamiento |
| --- | --- | --- |
| Roles solicitables desde registro público | Fase 3 | Corregir antes de confiar en permisos o autorización del Motor. |
| Refresh token aceptable como bearer de acceso | Fase 3 | Separar tipos de token antes de construir `ActorContext`. |
| Ausencia de deny-by-default uniforme | Fase 3 para superficies del Motor | Proteger únicamente las rutas y dependencias necesarias para el Motor; la cobertura general seguirá su propio proyecto. |
| Actor opcional en la excepción ETS | Fase 7, o antes si un contrato de Fase 4 lo consume | No integrar ese flujo mientras el actor no sea obligatorio. |
| Lógica y mutaciones ETS duplicadas | Fase 5/7 | Consolidar sólo las operaciones que serán invocadas por gateways. |
| Solicitud de excepción que ejecuta inmediatamente | Fase 7 | Separar solicitud, autorización y ejecución antes de modelar la resolución correspondiente. |
| Autenticación de certificados desde superficies duplicadas | Fase 9 al incorporar ese grupo | Mantener Calidad como mutador canónico antes de su gateway. |
| Deriva histórica de metadatos Alembic | Fase 2 sólo si interfiere con tablas, constraints o head del Motor | No corregir deriva ajena; aislar y validar la migración del Motor. |
| Falta de CI general | No bloquea Fases 0–9 por sí sola | Ejecutar localmente todas las validaciones requeridas; atenderla únicamente si impide evidencia reproducible de una fase. |

## Checklist obligatorio por apertura de fase

- [ ] La fase anterior está aprobada y tiene commit identificable.
- [ ] El estado de esta matriz marca únicamente la nueva fase como `ACTIVA`.
- [ ] Se enumeraron sus componentes autorizados.
- [ ] Se auditaron contradicciones directas en código y documentación.
- [ ] Cada corrección de deuda propuesta está ligada a un gate de la fase.
- [ ] Se excluyó explícitamente la deuda sin impacto directo.
- [ ] Se definieron pruebas y evidencia antes de escribir código.
- [ ] Se verificó que no se adelanten modelos, APIs o servicios posteriores.

## Checklist obligatorio de cierre de fase

- [ ] Todos los componentes autorizados quedaron completos.
- [ ] No se incorporaron componentes de fases posteriores.
- [ ] Se ejecutó la suite backend completa.
- [ ] Se ejecutaron pruebas frontend y build cuando correspondan.
- [ ] Se verificaron migraciones y PostgreSQL cuando correspondan.
- [ ] Se validó integración con el ERP sin regresiones funcionales.
- [ ] Se actualizaron los documentos indicados por `DOCUMENTATION_INDEX.md`.
- [ ] Se actualizó `docs/BACKUP_ESTADO_ACTUAL.md`.
- [ ] Se regeneró y revisó `docs/PROJECT_FILE_REGISTRY.md`.
- [ ] Se revisó `AGENTS.md` y se actualizó sólo si cambió una norma persistente.
- [ ] `git diff --check` terminó correctamente.
- [ ] El commit contiene exclusivamente la fase concluida.
- [ ] El estado cambió a `EN REVISIÓN` y el trabajo se detuvo.

## Evidencia de Fase 0

La Fase 0 se considera lista para revisión cuando:

- la especificación completa figure en el índice único;
- este documento figure en el inventario oficial;
- el README documente orden, precedencia y gobierno;
- el estado canónico identifique al Motor y su fase vigente;
- no se haya modificado código ni comportamiento funcional del ERP;
- las pruebas y validaciones del repositorio hayan sido ejecutadas;
- exista un commit exclusivo de cierre de Fase 0.

## Resultado de Fase 0

- Estado: `EN REVISIÓN`.
- Bloqueadores corregidos: clasificación canónica de la especificación, README
  normativo y matriz ejecutable de fases.
- Bloqueadores de código: ninguno aplicable a esta fase.
- Componentes adelantados: ninguno.
- Próxima fase autorizable: Fase 1, sólo después de aprobación expresa.
- Evidencia detallada:
  [`../../closures/RESOLUTION_ENGINE_PHASE_0.md`](../../closures/RESOLUTION_ENGINE_PHASE_0.md).

## Apertura de Fase 1

- Estado: `ACTIVA`.
- Autorización: aprobación expresa posterior al commit `4d66089`.
- Componentes autorizados: paquete fundacional, contratos tipados, catálogos,
  errores, hashing/serialización, reloj, identificadores, Registry y pruebas.
- Bloqueadores directos detectados al abrir: ninguno.
- Deuda general excluida: seguridad, ETS, excepciones, certificados, Alembic y
  demás condiciones asignadas a fases posteriores.

## Resultado de Fase 1

- Estado: `EN REVISIÓN`.
- Gate: cumplido; una definición nueva se registra mediante manifiesto sin
  condicionales ni cambios en el núcleo.
- Aislamiento: cubierto por pruebas AST contra ORM, servicios, routers,
  schemas, FastAPI, SQLAlchemy y paquetes de fases posteriores.
- Bloqueadores corregidos: ninguno; no se detectó contradicción directa que
  impidiera aislar la fundación.
- Componentes adelantados: ninguno.
- Próxima fase autorizable: Fase 2, sólo después de aprobación expresa.
- Evidencia detallada:
  [`../../closures/RESOLUTION_ENGINE_PHASE_1.md`](../../closures/RESOLUTION_ENGINE_PHASE_1.md).
