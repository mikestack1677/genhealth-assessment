from __future__ import annotations

import uuid  # noqa: TC003 — Pydantic resolves field types at runtime via get_type_hints()
from datetime import date, datetime  # noqa: TC003 — Pydantic resolves field types at runtime via get_type_hints()
from typing import Any

from pydantic import BaseModel

from genhealth.models.order import (
    OrderStatus,  # noqa: TC001 — Pydantic resolves field types at runtime via get_type_hints()
)


class OrderCreate(BaseModel):
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: date | None = None
    notes: str | None = None


class OrderUpdate(BaseModel):
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: date | None = None
    status: OrderStatus | None = None
    notes: str | None = None


class OrderDocumentAttach(BaseModel):
    """Payload for attaching extracted document data to an order."""

    filename: str
    extracted_data: dict[str, object]
    patient_first_name: str | None
    patient_last_name: str | None
    patient_dob: date | None


class OrderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_first_name: str | None
    patient_last_name: str | None
    patient_dob: date | None
    status: OrderStatus
    notes: str | None
    document_filename: str | None
    extracted_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
