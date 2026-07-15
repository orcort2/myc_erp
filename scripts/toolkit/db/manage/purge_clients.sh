#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

echo
echo "========================================"
echo "       VACIAR DATOS DE CLIENTES"
echo "========================================"
echo "Base: $DB_NAME"
echo

CLIENT_COUNT="$(psql "$DB_URL" -Atqc 'SELECT COUNT(*) FROM public.clients;')"
CONTACT_COUNT="$(psql "$DB_URL" -Atqc 'SELECT COUNT(*) FROM public.client_contacts;')"
PROFILE_COUNT="$(psql "$DB_URL" -Atqc 'SELECT COUNT(*) FROM public.client_certificate_profiles;')"

QUOTATION_COUNT="$(psql "$DB_URL" -Atqc '
  SELECT COUNT(*)
  FROM public.quotations
  WHERE client_id IS NOT NULL;
')"

SERVICE_ORDER_COUNT="$(psql "$DB_URL" -Atqc '
  SELECT COUNT(*)
  FROM public.service_orders
  WHERE client_id IS NOT NULL;
')"

INVOICE_COUNT="$(psql "$DB_URL" -Atqc '
  SELECT COUNT(*)
  FROM public.invoices
  WHERE client_id IS NOT NULL
     OR fiscal_client_id IS NOT NULL;
')"

echo "Registros encontrados:"
echo "  Clientes:                       $CLIENT_COUNT"
echo "  Contactos:                      $CONTACT_COUNT"
echo "  Perfiles de certificado:        $PROFILE_COUNT"
echo
echo "Dependencias históricas:"
echo "  Cotizaciones:                   $QUOTATION_COUNT"
echo "  Órdenes de servicio / ETS:      $SERVICE_ORDER_COUNT"
echo "  Facturas:                       $INVOICE_COUNT"
echo

if [[ "$QUOTATION_COUNT" != "0" ||
      "$SERVICE_ORDER_COUNT" != "0" ||
      "$INVOICE_COUNT" != "0" ]]; then
  echo "OPERACIÓN BLOQUEADA"
  echo
  echo "Existen clientes vinculados con información histórica."
  echo "No se borrará ningún registro."
  echo
  echo "Para borrar todo ese ecosistema tendrías que usar conscientemente"
  echo "TRUNCATE CASCADE, lo cual también eliminaría cotizaciones, ETS y facturas."
  exit 1
fi

if [[ "$CLIENT_COUNT" == "0" ]]; then
  echo "La tabla clients ya está vacía."
  exit 0
fi

echo "Se eliminarán físicamente:"
echo
echo "  - client_contacts"
echo "  - client_certificate_profiles"
echo "  - clients"
echo
echo "No se eliminarán cotizaciones, ETS ni facturas."
echo

EXPECTED_CONFIRMATION="ELIMINAR TODOS LOS CLIENTES"

read -r -p "Escribe exactamente '$EXPECTED_CONFIRMATION': " confirmation

if [[ "$confirmation" != "$EXPECTED_CONFIRMATION" ]]; then
  echo
  echo "Confirmación incorrecta."
  echo "No se modificó la base."
  exit 0
fi

read -r -p "¿Confirmas la eliminación definitiva? [s/N]: " final_confirmation

FINAL_NORMALIZED="$(
  printf '%s' "$final_confirmation" |
    tr '[:upper:]' '[:lower:]'
)"

case "$FINAL_NORMALIZED" in
  s|si)
    ;;
  *)
    echo
    echo "Operación cancelada."
    echo "No se modificó la base."
    exit 0
    ;;
esac

echo
echo "Eliminando datos de clientes..."

psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

DELETE FROM public.client_contacts;
DELETE FROM public.client_certificate_profiles;
DELETE FROM public.clients;

ALTER SEQUENCE IF EXISTS public.client_contacts_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.client_certificate_profiles_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.clients_id_seq RESTART WITH 1;

COMMIT;
SQL

REMAINING_CLIENTS="$(
  psql "$DB_URL" -Atqc 'SELECT COUNT(*) FROM public.clients;'
)"

REMAINING_CONTACTS="$(
  psql "$DB_URL" -Atqc 'SELECT COUNT(*) FROM public.client_contacts;'
)"

REMAINING_PROFILES="$(
  psql "$DB_URL" -Atqc \
    'SELECT COUNT(*) FROM public.client_certificate_profiles;'
)"

echo
echo "========================================"
echo "       OPERACIÓN TERMINADA"
echo "========================================"
echo "Clientes restantes:                $REMAINING_CLIENTS"
echo "Contactos restantes:               $REMAINING_CONTACTS"
echo "Perfiles restantes:                $REMAINING_PROFILES"
echo "Secuencias:                        reiniciadas"
echo "========================================"