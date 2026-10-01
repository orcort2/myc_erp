// The ordinary settings PATCH contains only user-configurable fields.
const EDITABLE_FIELDS = [
  'default_tax_rate', 'default_currency', 'default_credit_days',
  'forms_of_payment', 'methods_of_payment', 'usage_cfdi_catalog',
  'tax_regime_catalog', 'currency_catalog', 'sat_product_keys', 'sat_units',
  'banks', 'bank_accounts', 'legal_texts', 'billing_emails', 'emitter_data',
  'pdf_template_name', 'cfdi_future_parameters',
];

export function toInvoiceSettingsPayload(settings) {
  return Object.fromEntries(
    EDITABLE_FIELDS.filter((key) => Object.hasOwn(settings, key))
      .map((key) => [key, settings[key]])
  );
}
