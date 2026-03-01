from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from genhealth.schemas.document import DocumentExtractionResponse
from genhealth.services.document_service import DocumentService
from genhealth.services.llm_providers import get_llm_provider
from genhealth.services.llm_providers.base import (
    LLMProvider,  # noqa: TC001 — FastAPI resolves Annotated[LLMProvider, Depends(...)] via get_type_hints() at runtime
)

logger = structlog.get_logger()
router = APIRouter()


def get_document_service(provider: Annotated[LLMProvider, Depends(get_llm_provider)]) -> DocumentService:
    """FastAPI dependency: construct DocumentService with the configured LLM provider."""
    return DocumentService(provider)


@router.post("/documents/extract", response_model=DocumentExtractionResponse)
async def extract_document(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentExtractionResponse:
    """Extract patient data from a standalone PDF (not attached to any order)."""
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    pdf_bytes = await file.read()
    filename = file.filename or "document.pdf"

    extracted = await service.extract_patient_data(pdf_bytes, filename)

    logger.info(
        "standalone_document_extracted",
        filename=filename,
        found_first_name=extracted.first_name is not None,
        found_last_name=extracted.last_name is not None,
        found_dob=extracted.date_of_birth is not None,
    )

    return DocumentExtractionResponse(extracted=extracted, filename=filename)
