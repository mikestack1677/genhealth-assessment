from __future__ import annotations

import asyncio
import base64
import io
import json
import re

import anthropic
import structlog
from fastapi import HTTPException, status
from pypdf import PdfReader

from genhealth.core.config import get_settings
from genhealth.schemas.document import ExtractedPatientData

logger = structlog.get_logger()

_EXTRACT_PROMPT = """
You are a medical records assistant. Extract the following patient information from the provided document.
Respond ONLY with a JSON object — no prose, no markdown, no code fences.

Required JSON format:
{"first_name": "...", "last_name": "...", "date_of_birth": "YYYY-MM-DD"}

If a field cannot be found, use null for that field.
Do not include any text outside the JSON object.
""".strip()


class DocumentService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    async def extract_patient_data(self, pdf_bytes: bytes, filename: str) -> ExtractedPatientData:
        """Extract patient information from a PDF using Claude."""
        self._validate_file_size(pdf_bytes, filename)
        self._validate_page_count(pdf_bytes, filename)
        return await self._call_claude_with_retry(pdf_bytes, filename)

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

    async def _call_claude_with_retry(self, pdf_bytes: bytes, filename: str) -> ExtractedPatientData:
        """Send PDF to Claude with exponential backoff retry on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(self._settings.llm_max_retries + 1):
            if attempt > 0:
                backoff = 2**attempt
                logger.warning(
                    "claude_retry",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    filename=filename,
                )
                await asyncio.sleep(backoff)
            try:
                return await self._call_claude(pdf_bytes, filename)
            except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
                last_exc = exc
                logger.warning(
                    "claude_transient_error",
                    attempt=attempt,
                    error=str(exc),
                    filename=filename,
                )
                continue
            except anthropic.APIError as exc:
                logger.exception("claude_api_error", error=str(exc), filename=filename)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Document extraction failed: {exc}",
                ) from exc

        logger.error(
            "claude_all_retries_exhausted",
            attempts=self._settings.llm_max_retries + 1,
            filename=filename,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document extraction failed after {self._settings.llm_max_retries + 1} attempts: {last_exc}",
        )

    async def _call_claude(self, pdf_bytes: bytes, filename: str) -> ExtractedPatientData:
        """Make a single Claude API call and parse the response."""
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

        response = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=self._settings.llm_max_tokens,
            timeout=self._settings.llm_request_timeout_seconds,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": _EXTRACT_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw_text = response.content[0].text if response.content else ""  # type: ignore[union-attr]
        return self._parse_response(raw_text, filename)

    def _parse_response(self, raw_text: str, filename: str) -> ExtractedPatientData:
        """Parse Claude's JSON response into ExtractedPatientData."""
        text = raw_text.strip()
        # Strip markdown code fences if Claude wraps the JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning("claude_no_json_found", raw=text[:200], filename=filename)
            return ExtractedPatientData()

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            logger.warning("claude_json_decode_error", error=str(exc), raw=text[:200], filename=filename)
            return ExtractedPatientData()

        return ExtractedPatientData(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            date_of_birth=data.get("date_of_birth"),
        )
