from __future__ import annotations

from datetime import date  # noqa: TC003 — Pydantic resolves field types at runtime via get_type_hints()

from pydantic import BaseModel


class ExtractedPatientData(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None


class DocumentExtractionResponse(BaseModel):
    extracted: ExtractedPatientData
    filename: str
