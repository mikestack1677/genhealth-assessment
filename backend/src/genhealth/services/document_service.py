from __future__ import annotations

import io
import json
import re
from typing import TYPE_CHECKING

import structlog
from fastapi import HTTPException, status
from pypdf import PdfReader

from genhealth.core.config import get_settings
from genhealth.schemas.document import ExtractedPatientData

if TYPE_CHECKING:
    from genhealth.services.llm_providers.base import LLMProvider

logger = structlog.get_logger()


class DocumentService:
    def __init__(self, provider: LLMProvider) -> None:
        self._settings = get_settings()
        self._provider = provider

    async def extract_patient_data(self, pdf_bytes: bytes, filename: str) -> ExtractedPatientData:
        """Extract patient information from a PDF using the configured LLM provider."""
        self._validate_file_size(pdf_bytes, filename)
        self._validate_page_count(pdf_bytes, filename)
        raw = await self._provider.extract(pdf_bytes, filename)
        return self._parse_response(raw, filename)

    def _validate_file_size(self, pdf_bytes: bytes, filename: str) -> None:
        max_bytes = self._settings.llm_max_file_size_mb * 1024 * 1024
        if len(pdf_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{filename}' exceeds maximum allowed size of {self._settings.llm_max_file_size_mb} MB",
            )

    def _validate_page_count(self, pdf_bytes: bytes, filename: str) -> None:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read PDF '{filename}': {exc}",
            ) from exc

        if page_count > self._settings.llm_max_pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"PDF '{filename}' has {page_count} pages, exceeding the maximum of {self._settings.llm_max_pages}"
                ),
            )

    def _parse_response(self, raw_text: str, filename: str) -> ExtractedPatientData:
        """Parse the LLM JSON response into ExtractedPatientData."""
        text = raw_text.strip()
        # Strip markdown code fences if the LLM wraps the JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning("llm_no_json_found", raw=text[:200], filename=filename)
            return ExtractedPatientData()

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            logger.warning("llm_json_decode_error", error=str(exc), raw=text[:200], filename=filename)
            return ExtractedPatientData()

        return ExtractedPatientData(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            date_of_birth=data.get("date_of_birth"),
        )
