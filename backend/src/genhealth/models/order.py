from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from genhealth.models.base import Base, TimestampMixin, UUIDv7PrimaryKey

if TYPE_CHECKING:
    from genhealth.models.activity_log import ActivityLog


class OrderStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


class Order(UUIDv7PrimaryKey, TimestampMixin, Base):
    __tablename__ = "orders"

    patient_first_name: Mapped[str | None] = mapped_column(String(255))
    patient_last_name: Mapped[str | None] = mapped_column(String(255))
    patient_dob: Mapped[date | None] = mapped_column(Date())
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orderstatus", values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    notes: Mapped[str | None] = mapped_column(Text())
    document_filename: Mapped[str | None] = mapped_column(String(512))
    extracted_data: Mapped[dict | None] = mapped_column(JSON())
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        "ActivityLog",
        back_populates="order",
        lazy="raise",
    )
