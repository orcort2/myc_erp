from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SatCatalogVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    publication_date: date | None = None
    imported_at: datetime
    checksum: str
    source_filename: str
    imported_by_id: int | None = None
    record_count: int
    status: str
    report: dict | None = None


class SatCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    installed_version: SatCatalogVersionRead | None = None


class SatCatalogRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool
    is_current: bool = True
    is_favorite: bool = False
    matched_on: list[str] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)


class SatCatalogRecordPage(BaseModel):
    catalog: str
    version: str
    total: int
    items: list[SatCatalogRecordRead] = Field(default_factory=list)


class SatCatalogAliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=500)


class SatCatalogAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog_record_id: int
    alias: str
    normalized_alias: str
    is_active: bool
    created_by_id: int
    created_at: datetime


class SatCatalogFavoriteCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class SatCatalogFavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog_record_id: int
    created_by_id: int
    notes: str | None = None
    created_at: datetime
