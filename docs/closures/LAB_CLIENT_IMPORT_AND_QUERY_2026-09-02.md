> Estado: CIERRE TÉCNICO VALIDADO
>
> Fecha: 2026-09-02
>
> Alcance: LabClient / MYC Mobile LAB

# Importación y consulta eficiente de LabClient

## Resultado

El importador dejó de depender de encabezados literales y ahora persiste los
campos estructurados ya presentes en `LabClient`. La API única de listado
aplica búsqueda y paginación en SQL; el selector OT evita consultas vacías y
la administración carga páginas de 25 sin cambiar el contrato array.

## Contratos verificados

- XLSX obligatorio: `CLIENTE`, `CONTACTO|ATENCION|ATENCIÓN` y
  `DIRECCIÓN|DIRECCION`.
- Opcional: `CÓDIGO POSTAL|CODIGO POSTAL|CP|C.P.`, `CIUDAD`, `ESTADO`.
- Ignorado: `DIRECCIÓN ORIGINAL`, `REVISAR` y cualquier encabezado no
  reconocido.
- GET: `search` opcional, `include_inactive=false`, `offset=0`, `limit=25`
  (1..100), respuesta `LabClient[]` y orden estable por empresa, atención e ID.
- Selector: cero/uno caracteres no consultan; dos o más usan 300 ms y límite 5.
- Administración: búsqueda remota, páginas de 25, reemplazo al cambiar filtro y
  agregado deduplicado con “Cargar más”.

## Persistencia y límites

No hubo migración ni cambio de base. Se verificaron índices existentes sobre
`operator_client_id` y `company`; con el volumen informado, añadir índice de
`is_active` o trigramas no está sustentado. La corrección elimina la
transferencia/serialización masiva sin tocar `Client` productivo.

## Evidencia automática

- Backend: 6 pruebas focales de importación; 10 de dominio/listado; 1 de scope.
- Mobile: 17 focales y 273 en la suite completa.
- TypeScript: correcto.
- Lint: 0 errores; 6 warnings preexistentes fuera del alcance.
- Pendiente operativo: aceptación manual en dispositivo de ambos recorridos;
  no bloquea el contrato automatizado y no autoriza declarar OT LAB SELLADO.
