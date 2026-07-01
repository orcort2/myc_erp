from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Certificate(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "certificates"

    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    expected_folio: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    field_sheet_id: Mapped[int | None] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    certificate_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    issued_on: Mapped[date | None] = mapped_column(Date)
    released_on: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)
    final_pdf_path: Mapped[str | None] = mapped_column(String(255))
    final_pdf_original_filename: Mapped[str | None] = mapped_column(String(255))
    final_pdf_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_pdf_uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    capture_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    capture_started_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    sent_to_quality_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_to_quality_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    quality_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    quality_rejection_reason: Mapped[str | None] = mapped_column(Text)
    released_to_client_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_to_client_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    authentication_code: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    authentication_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    authenticated_pdf_path: Mapped[str | None] = mapped_column(String(255))
    authenticated_pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authenticated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    verification_url: Mapped[str | None] = mapped_column(String(255))
    external_source: Mapped[str] = mapped_column(String(40), default="excel", index=True)
    match_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    match_details: Mapped[dict | None] = mapped_column(JSON)
    client_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="certificates")
    equipment: Mapped["Equipment"] = relationship(back_populates="certificates")
    field_sheet: Mapped["FieldSheet | None"] = relationship(back_populates="certificates")
