import { listSatCatalogRecords } from '../../services/api.js';

const INVOICE_DEFAULT_CODES = {
  voucherType: ['voucher_types', 'I'],
  paymentForm: ['payment_forms', '03'],
  paymentMethod: ['payment_methods', 'PUE'],
  currency: ['currencies', 'MXN'],
  export: ['exports', '01'],
  country: ['countries', 'MEX'],
  taxObject: ['tax_objects', '02'],
  tax: ['taxes', '002'],
  factorType: ['factor_types', 'Tasa'],
  taxRate: ['tax_rates', '0.160000'],
  productService: ['products_services', '81141504'],
  unit: ['units', 'E48'],
};

function normalizeCatalogCode(value) {
  return String(value ?? '').trim().toUpperCase();
}

function catalogCodesMatch(actualCode, expectedCode) {
  const actual = normalizeCatalogCode(actualCode);
  const expected = normalizeCatalogCode(expectedCode);

  if (actual === expected) return true;
  if (/^\d+$/.test(actual) && /^\d+$/.test(expected)) {
    return Number(actual) === Number(expected);
  }
  return false;
}

function toCatalogSelection(record) {
  return record?.code
    ? { id: record.id ?? null, code: String(record.code).trim(), name: record.name || '' }
    : null;
}

async function resolveCatalogRecord(catalogCode, expectedCode, cache) {
  const expected = normalizeCatalogCode(expectedCode);
  if (!expected) return null;
  const key = `${catalogCode}:${expected}`;
  if (!cache.has(key)) {
    cache.set(key, (async () => {
      try {
        const result = await listSatCatalogRecords(catalogCode, {
          search: String(expectedCode).trim(),
          limit: 25,
        });
        return toCatalogSelection(
          (Array.isArray(result?.items) ? result.items : []).find((record) =>
            catalogCodesMatch(record?.code, expected)
          )
        );
      } catch {
        return null;
      }
    })());
  }
  return cache.get(key);
}

export async function buildInvoiceWorkbenchDraft(quotation, client, invoice = null) {
  const cache = new Map();
  const fiscalSnapshot = invoice?.fiscal_snapshot || null;
  const receiver = {
    rfc: fiscalSnapshot?.receiver_rfc || client?.rfc || '',
    legalName: fiscalSnapshot?.receiver_legal_name || client?.legal_name || '',
    fiscalRegimeCode: fiscalSnapshot?.receiver_tax_regime_code || client?.tax_regime || '',
    fiscalPostalCode: fiscalSnapshot?.receiver_fiscal_postal_code || client?.fiscal_postal_code || '',
    cfdiUseCode: fiscalSnapshot?.receiver_cfdi_use_code || invoice?.usage_cfdi || client?.cfdi_use || '',
    countryCode: fiscalSnapshot?.receiver_country_code || client?.fiscal_country_code || 'MEX',
  };
  const resolveDefault = (key) => {
    const [catalogCode, code] = INVOICE_DEFAULT_CODES[key];
    return resolveCatalogRecord(catalogCode, code, cache);
  };
  const [voucherType, defaultPaymentForm, defaultPaymentMethod, defaultCurrency, exportValue, country, defaultTaxObject, defaultTax, defaultFactorType, defaultTaxRate, defaultProductService, defaultUnit, cfdiUse, fiscalRegime, fiscalPostalCode] = await Promise.all([
    resolveDefault('voucherType'), resolveDefault('paymentForm'), resolveDefault('paymentMethod'), resolveDefault('currency'),
    resolveDefault('export'), resolveDefault('country'), resolveDefault('taxObject'), resolveDefault('tax'),
    resolveDefault('factorType'), resolveDefault('taxRate'), resolveDefault('productService'), resolveDefault('unit'),
    resolveCatalogRecord('cfdi_uses', receiver.cfdiUseCode, cache),
    resolveCatalogRecord('fiscal_regimes', receiver.fiscalRegimeCode, cache),
    resolveCatalogRecord('postal_codes', receiver.fiscalPostalCode, cache),
  ]);

  const invoiceItemsByQuotationItemId = new Map(
    (invoice?.items || []).filter((item) => item.quotation_item_id).map((item) => [String(item.quotation_item_id), item])
  );
  const concepts = Object.fromEntries(await Promise.all(
    (quotation?.items || []).filter((item) => item.is_active !== false).map(async (item) => {
      const persisted = invoiceItemsByQuotationItemId.get(String(item.id));
      const [productService, unit, taxObject] = await Promise.all([
        resolveCatalogRecord('products_services', persisted?.sat_key || item.sat_key, cache),
        resolveCatalogRecord('units', persisted?.sat_unit || item.sat_unit, cache),
        resolveCatalogRecord('tax_objects', item.tax_object, cache),
      ]);
      return [item.id, {
        productService: productService || defaultProductService,
        unit: unit || defaultUnit,
        taxObject: taxObject || defaultTaxObject,
        tax: defaultTax,
        factorType: defaultFactorType,
        taxRate: defaultTaxRate,
      }];
    })
  ));

  return {
    voucherType,
    cfdiUse,
    paymentForm: invoice?.payment_form
      ? await resolveCatalogRecord('payment_forms', invoice.payment_form, cache)
      : defaultPaymentForm,
    paymentMethod: invoice?.payment_method
      ? await resolveCatalogRecord('payment_methods', invoice.payment_method, cache)
      : defaultPaymentMethod,
    currency: invoice?.currency
      ? await resolveCatalogRecord('currencies', invoice.currency, cache)
      : defaultCurrency,
    export: exportValue,
    country,
    relationType: null,
    fiscalRegime,
    fiscalPostalCode,
    receiver,
    concepts,
  };
}
