from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FolioRequest:
    document_type: str
    sequence: int
    service_type: str | None = None
    issued_on: date | None = None


def generate_folio(request: FolioRequest) -> str:
    issued_on = request.issued_on or date.today()
    sequence = f"{request.sequence:04d}"

    match request.document_type:
        case "cotizacion":
            return f"MYC-{issued_on:%m}-{issued_on:%y}-{sequence}"
        case "agenda":
            return f"AMYC-{issued_on:%y}-{issued_on:%m}-{sequence}"
        case "llamado":
            return f"SMYC-{issued_on:%y}-{issued_on:%m}-{sequence}"
        case "orden_servicio":
            return f"OSMYC-{issued_on:%y}-{issued_on:%m}-{sequence}"
        case "certificado":
            if request.service_type == "acreditado":
                prefix = "A"
            elif request.service_type == "vinculado":
                prefix = "V"
            else:
                prefix = "T"
            return f"MYC{prefix}-{issued_on:%m}-{issued_on:%Y}-{sequence}"
        case _:
            raise ValueError(f"Tipo de folio no soportado: {request.document_type}")
