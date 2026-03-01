from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from genhealth.core.config import Settings, get_settings
from genhealth.schemas.document import DocumentExtractionResponse
from genhealth.services.document_service import DocumentService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/documents/extract", response_model=DocumentExtractionResponse)
async def extract_document(
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
) -> DocumentExtractionResponse:
    """Extract patient data from a standalone PDF (not attached to any order)."""
    _ = settings  # accessed for rate-limit config; limiter applied at app level

    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    pdf_bytes = await file.read()
    filename = file.filename or "document.pdf"

    service = DocumentService()
    extracted = await service.extract_patient_data(pdf_bytes, filename)

    logger.info(
        "standalone_document_extracted",
        filename=filename,
        found_first_name=extracted.first_name is not None,
        found_last_name=extracted.last_name is not None,
        found_dob=extracted.date_of_birth is not None,
    )

    return DocumentExtractionResponse(extracted=extracted, filename=filename)
