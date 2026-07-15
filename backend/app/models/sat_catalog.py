from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class SatCatalog(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sat_catalogs"

    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)

    versions: Mapped[list["SatCatalogVersion"]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan"
    )


class SatCatalogVersion(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sat_catalog_versions"
    __table_args__ = (
        UniqueConstraint("catalog_id", "version", name="uq_sat_catalog_version"),
        UniqueConstraint("catalog_id", "checksum", name="uq_sat_catalog_checksum"),
    )

    catalog_id: Mapped[int] = mapped_column(ForeignKey("sat_catalogs.id"), index=True)
    version: Mapped[str] = mapped_column(String(120))
    publication_date: Mapped[date | None] = mapped_column(Date)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128))
    source_filename: Mapped[str] = mapped_column(String(255))
    imported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    record_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="imported", index=True)
    report: Mapped[dict | None] = mapped_column(JSON)

    catalog: Mapped[SatCatalog] = relationship(back_populates="versions")
    records: Mapped[list["SatCatalogRecord"]] = relationship(
        back_populates="catalog_version", cascade="all, delete-orphan"
    )


class SatCatalogRecord(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sat_catalog_records"
    __table_args__ = (
        UniqueConstraint("catalog_version_id", "code", name="uq_sat_catalog_record_version_code"),
    )

    catalog_version_id: Mapped[int] = mapped_column(ForeignKey("sat_catalog_versions.id"), index=True)
    code: Mapped[str] = mapped_column(String(120), index=True)
    normalized_code: Mapped[str] = mapped_column(String(120), index=True, default="")
    name: Mapped[str | None] = mapped_column(Text, index=True)
    normalized_name: Mapped[str] = mapped_column(Text, default="")
    search_text: Mapped[str] = mapped_column(Text, default="")
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    catalog_version: Mapped[SatCatalogVersion] = relationship(back_populates="records")
    favorites: Mapped[list["SatCatalogFavorite"]] = relationship(back_populates="catalog_record", cascade="all, delete-orphan")
    aliases: Mapped[list["SatCatalogAlias"]] = relationship(back_populates="catalog_record", cascade="all, delete-orphan")


class SatCatalogFavorite(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sat_catalog_favorites"
    __table_args__ = (UniqueConstraint("catalog_record_id", "created_by_id", name="uq_sat_catalog_favorite_user_record"),)

    catalog_record_id: Mapped[int] = mapped_column(ForeignKey("sat_catalog_records.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    catalog_record: Mapped[SatCatalogRecord] = relationship(back_populates="favorites")


class SatCatalogAlias(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sat_catalog_aliases"
    __table_args__ = (UniqueConstraint("catalog_record_id", "normalized_alias", name="uq_sat_catalog_alias_record_normalized"),)

    catalog_record_id: Mapped[int] = mapped_column(ForeignKey("sat_catalog_records.id"), index=True)
    alias: Mapped[str] = mapped_column(String(500))
    normalized_alias: Mapped[str] = mapped_column(String(600), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    catalog_record: Mapped[SatCatalogRecord] = relationship(back_populates="aliases")
