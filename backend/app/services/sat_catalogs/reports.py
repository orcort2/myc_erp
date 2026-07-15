from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SatCatalogImportReport:
    catalog: str
    version: str
    source_filename: str
    checksum: str
    status: str
    record_count: int
    message: str

    def as_dict(self) -> dict:
        return asdict(self)
