#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

TABLE="${1:-}"

if [[ -z "$TABLE" ]]; then
  read -r -p "Nombre exacto de la tabla: " TABLE
fi

validate_table_name "$TABLE"

COUNT="$(get_table_count "$TABLE")"
DEPENDENCIES="$(list_dependent_tables "$TABLE" || true)"

echo
echo "========================================"
echo "       ADMINISTRAR VACIADO"
echo "========================================"
echo "Base:      $DB_NAME"
echo "Tabla:     $TABLE"
echo "Registros: $COUNT"
echo

if [[ -n "$DEPENDENCIES" ]]; then
  echo "Tablas que dependen mediante llaves foráneas:"
  echo

  while IFS='|' read -r dependent_table dependent_column referenced_column; do
    printf "  - %s.%s -> %s.%s\n" \
      "$dependent_table" \
      "$dependent_column" \
      "$TABLE" \
      "$referenced_column"
  done <<< "$DEPENDENCIES"
else
  echo "No se detectaron tablas dependientes."
fi

echo
echo "Selecciona el modo de eliminación:"
echo
echo "1) DELETE sólo sobre '$TABLE'"
echo "   Intenta eliminar únicamente los registros de esta tabla."
echo "   Si existen dependencias, PostgreSQL bloqueará la operación."
echo
echo "2) TRUNCATE sólo sobre '$TABLE'"
echo "   Vacía la tabla y reinicia sus IDs."
echo "   Si existen dependencias, PostgreSQL bloqueará la operación."
echo
echo "3) TRUNCATE CASCADE"
echo "   Vacía la tabla, reinicia IDs y también vacía tablas dependientes."
echo "   Esta opción es altamente destructiva."
echo
echo "0) Cancelar"
echo

read -r -p "Elige una opción: " DELETE_MODE

case "$DELETE_MODE" in
  1)
    MODE_LABEL="DELETE"
    SQL_COMMAND="DELETE FROM public.\"$TABLE\";"
    CONFIRMATION_PREFIX="ELIMINAR"
    ;;
  2)
    MODE_LABEL="TRUNCATE"
    SQL_COMMAND="TRUNCATE TABLE public.\"$TABLE\" RESTART IDENTITY;"
    CONFIRMATION_PREFIX="VACIAR"
    ;;
  3)
    MODE_LABEL="TRUNCATE CASCADE"
    SQL_COMMAND="TRUNCATE TABLE public.\"$TABLE\" RESTART IDENTITY CASCADE;"
    CONFIRMATION_PREFIX="VACIAR TODO"
    ;;
  0)
    echo
    echo "Operación cancelada. No se modificó la base."
    exit 0
    ;;
  *)
    echo
    echo "Opción inválida. No se modificó la base."
    exit 1
    ;;
esac

TABLE_UPPER="$(printf '%s' "$TABLE" | tr '[:lower:]' '[:upper:]')"
EXPECTED_CONFIRMATION="$CONFIRMATION_PREFIX $TABLE_UPPER"

echo
echo "========================================"
echo "       CONFIRMACIÓN"
echo "========================================"
echo "Modo:      $MODE_LABEL"
echo "Base:      $DB_NAME"
echo "Tabla:     $TABLE"
echo "Registros: $COUNT"
echo
echo "Comando que se ejecutará:"
echo
echo "$SQL_COMMAND"
echo

if [[ "$DELETE_MODE" == "3" && -n "$DEPENDENCIES" ]]; then
  echo "ADVERTENCIA:"
  echo "TRUNCATE CASCADE también vaciará las tablas dependientes"
  echo "mostradas anteriormente."
  echo
fi

read -r -p "Escribe exactamente '$EXPECTED_CONFIRMATION': " confirmation

if [[ "$confirmation" != "$EXPECTED_CONFIRMATION" ]]; then
  echo
  echo "Confirmación incorrecta."
  echo "Operación cancelada. No se modificó la base."
  exit 0
fi

read -r -p "¿Confirmas la operación definitiva? [s/N]: " final_confirmation

case "$(printf '%s' "$final_confirmation" | tr '[:upper:]' '[:lower:]')" in
  s|si)
    ;;
  *)
    echo
    echo "Operación cancelada. No se modificó la base."
    exit 0
    ;;
esac

echo
echo "Ejecutando operación..."

if ! psql "$DB_URL" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
$SQL_COMMAND
COMMIT;
SQL
then
  echo
  echo "ERROR: PostgreSQL rechazó la operación."
  echo
  echo "No se aplicaron cambios porque la transacción fue revertida."
  echo

  if [[ "$DELETE_MODE" == "1" || "$DELETE_MODE" == "2" ]]; then
    echo "Es probable que existan registros relacionados en otras tablas."
    echo "Puedes revisar las dependencias mostradas arriba."
    echo
    echo "No uses CASCADE salvo que también quieras eliminar esos datos."
  fi

  exit 1
fi

REMAINING="$(get_table_count "$TABLE")"

echo
echo "========================================"
echo "       OPERACIÓN TERMINADA"
echo "========================================"
echo "Modo:                 $MODE_LABEL"
echo "Tabla:                $TABLE"
echo "Registros anteriores: $COUNT"
echo "Registros restantes:  $REMAINING"

if [[ "$DELETE_MODE" == "1" ]]; then
  echo "Secuencia de IDs:     sin cambios"
else
  echo "Secuencia de IDs:     reiniciada"
fi

if [[ "$DELETE_MODE" == "3" ]]; then
  echo "Dependencias:         aplicadas mediante CASCADE"
fi

echo "========================================"