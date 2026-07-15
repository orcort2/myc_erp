from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogDefinition:
    code: str
    name: str
    description: str


CATALOG_DEFINITIONS = (
    CatalogDefinition("products_services", "Productos y servicios", "c_ClaveProdServ"),
    CatalogDefinition("units", "Unidades", "c_ClaveUnidad"),
    CatalogDefinition("fiscal_regimes", "Régimen fiscal", "c_RegimenFiscal"),
    CatalogDefinition("cfdi_uses", "Uso CFDI", "c_UsoCFDI"),
    CatalogDefinition("payment_forms", "Formas de pago", "c_FormaPago"),
    CatalogDefinition("payment_methods", "Métodos de pago", "c_MetodoPago"),
    CatalogDefinition("currencies", "Monedas", "c_Moneda"),
    CatalogDefinition("countries", "Países", "c_Pais"),
    CatalogDefinition("postal_codes", "Códigos postales", "c_CodigoPostal"),
    CatalogDefinition("tax_objects", "Objeto de impuesto", "c_ObjetoImp"),
    CatalogDefinition("relation_types", "Tipos de relación", "c_TipoRelacion"),
    CatalogDefinition("cancellation_reasons", "Motivos de cancelación", "c_MotivoCancelacion"),
    CatalogDefinition("exports", "Exportación", "c_Exportacion"),
    CatalogDefinition("taxes", "Impuestos", "c_Impuesto"),
    CatalogDefinition("factor_types", "Tipos de factor", "c_TipoFactor"),
    CatalogDefinition("tax_rates", "Tasas o cuotas", "c_TasaOCuota"),
    CatalogDefinition("voucher_types", "Tipos de comprobante", "c_TipoDeComprobante"),
)

DEFINITIONS_BY_CODE = {definition.code: definition for definition in CATALOG_DEFINITIONS}
