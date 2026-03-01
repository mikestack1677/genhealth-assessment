from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from genhealth.models.base import Base, UUIDv7PrimaryKey

if TYPE_CHECKING:
    from genhealth.models.order import Order


class ActivityLog(UUIDv7PrimaryKey, Base):
    __tablename__ = "activity_logs"

    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(2048))
    status_code: Mapped[int] = mapped_column(Integer())
    request_summary: Mapped[str | None] = mapped_column(Text())
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    duration_ms: Mapped[int] = mapped_column(Integer())
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order | None] = relationship(
        "Order",
        back_populates="activity_logs",
        lazy="raise",
    )
