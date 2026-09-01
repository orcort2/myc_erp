from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabClient(IntegerPkMixin, TimestampMixin, Base):
    """Cliente mínimo del vertical temporal LAB, aislado del catálogo fiscal."""

    __tablename__ = "lab_clients"
    __table_args__ = (
        UniqueConstraint(
            "operator_client_id",
            "normalized_company",
            "normalized_address",
            "normalized_attention",
            name="uq_lab_clients_tenant_normalized_identity",
        ),
    )

    operator_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    attention: Mapped[str] = mapped_column(String(180), nullable=False)
    normalized_company: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_address: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_attention: Mapped[str] = mapped_column(String(180), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    operator_client: Mapped["Client | None"] = relationship()
    created_by: Mapped["User"] = relationship()


from app.models.client import Client  # noqa: E402
from app.models.user import User  # noqa: E402
