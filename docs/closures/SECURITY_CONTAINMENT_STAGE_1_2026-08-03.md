> Estado: TERMINADA — EN REVISIÓN
>
> Fecha: 2026-08-03
>
> Alcance: contención transversal de seguridad, sin cambios de esquema

# Cierre técnico de Contención de Seguridad — Etapa 1

## Resultado

Se cerró el bloque ejecutable de AUD-001, AUD-002 y AUD-003. La API interna
quedó bajo deny-by-default, el portal deriva y valida su cliente sin aceptar un
tenant del request, el IDOR de PDF devuelve 404 seguro y producción rechaza un
secreto JWT inseguro. AUD-011 quedó cerrado para navegación y acciones
principales; AUD-013 quedó cerrado para la matriz HTTP automatizada de esta
etapa. AUD-010 conserva fuera de alcance la revocación/rotación y el
almacenamiento en `localStorage`.

## Evidencia de clasificación

| Categoría | Operaciones finales |
| --- | ---: |
| Pública intencional | 6 |
| Pública firmada | 1 |
| Pública controlada por entorno | 1 |
| Consumidor API Motor | 4 |
| Autenticada | 6 |
| Autenticada con permiso | 270 |
| Autenticada con ownership | 5 |
| Portal con ownership | 4 |
| Administrativa | 9 |
| **Total** | **306** |

El corte anterior reportó 74 operaciones públicas/no protegidas y 15 con actor
opcional. El corte actual tiene seis públicas básicas; al sumar verificación
firmada, portal técnico controlado por entorno y Motor con seguridad propia hay
12 excepciones intencionales. No queda una dependencia de usuario opcional en
routers internos; sólo existe el extractor bearer opcional sin autoridad que
necesita el guard central para distinguir público de 401.

## Controles implementados

- clasificación canónica por operación y prueba que falla con una ruta nueva;
- guard transversal aplicado al incluir todos los routers;
- permisos backend ampliados para capacidades ya existentes y actor obligatorio
  en Cotizaciones/ETS;
- bootstrap público limitado al primer Administrador;
- tipos access/refresh estrictos, firma/expiración/usuario activo verificados;
- validación productiva de longitud, diversidad y entropía de `SECRET_KEY`;
- portal `Cliente` con vínculo único fail-closed, filtros por cliente, ownership
  en descarga y auditoría de accesos válidos;
- navegación, Dashboard, Ajustes, Centro de Resoluciones, Facturación, Clientes,
  Cotizaciones y liberación de Certificados condicionados por permisos efectivos;
- mensajes diferenciados para 401, 403 y fallo de red.

## Validaciones

| Validación | Resultado |
| --- | --- |
| Suite backend completa | 427 passed, 19 subtests passed, 2 warnings |
| Seguridad dirigida | 22 passed |
| Frontend completo con `node --test` | 31 passed |
| Build Vite | correcto; warning preexistente de chunk >500 kB |
| Inventario/conformidad | 306/306 clasificadas; CSV coincide con runtime |
| Dos clientes/IDOR | A→A 200, A→B 404, B→B 200, B→A 404; anónimo 401 |
| Compilación Python | correcta |
| Búsqueda de sesión opcional | sin dependencia opcional de usuario en routers |
| Migraciones/esquema/base compartida | no modificados ni ejecutados |

Los dos warnings backend son deprecaciones de Starlette/httpx y passlib/crypt;
no son fallos de la etapa. El warning Vite corresponde al tamaño del bundle y
permanece fuera del alcance autorizado.

## Riesgos que permanecen fuera de esta etapa

- access/refresh siguen en `localStorage`; no hay jti, rotación, revocación,
  recuperación de contraseña ni MFA;
- no se implementó rate limiting;
- el vínculo del portal se resuelve contra correo principal/contacto porque una
  FK nueva requeriría migración; la ambigüedad se deniega;
- uploads, CORS, CI/CD, observabilidad, CFDI y deuda de esquema permanecen para
  sus etapas propias.

## Archivos de evidencia primaria

- `backend/app/security/api_access.py`
- `backend/app/services/client_portal.py`
- `backend/tests/test_api_access_conformity.py`
- `backend/tests/test_security_containment_stage_1.py`
- `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
- `docs/architecture/security/API_ACCESS_CONTROL.md`

Este documento acredita terminación técnica, no aprobación. El estado se
mantiene **TERMINADA — EN REVISIÓN** hasta dictamen del usuario.
