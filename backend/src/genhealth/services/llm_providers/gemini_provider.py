from __future__ import annotations

import asyncio

import structlog
from fastapi import HTTPException, status
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from genhealth.core.config import get_settings
from genhealth.services.llm_providers.base import LLMProvider

logger = structlog.get_logger()

_EXTRACT_PROMPT = """
You are a medical records assistant. Extract the following patient information from the provided document.
Respond ONLY with a JSON object — no prose, no markdown, no code fences.

Required JSON format:
{"first_name": "...", "last_name": "...", "date_of_birth": "YYYY-MM-DD"}

If a field cannot be found, use null for that field.
Do not include any text outside the JSON object.
""".strip()

_GEMINI_MODEL = "gemini-2.0-flash"

# HTTP status code for rate limiting
_HTTP_RATE_LIMIT = 429


class GeminiProvider(LLMProvider):
    """LLM provider backed by Google Gemini."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = genai.Client(api_key=self._settings.google_api_key)

    async def extract(self, pdf_bytes: bytes, filename: str) -> str:
        """Send PDF to Gemini with exponential backoff retry on transient errors.

        Returns the raw text response expected to contain JSON.
        Raises HTTPException(422) on non-transient errors or exhausted retries.
        """
        last_exc: Exception | None = None
        for attempt in range(self._settings.llm_max_retries + 1):
            if attempt > 0:
                backoff = 2**attempt
                logger.warning(
                    "gemini_retry",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    filename=filename,
                )
                await asyncio.sleep(backoff)
            try:
                return await self._call_api(pdf_bytes, filename)
            except genai_errors.ServerError as exc:
                last_exc = exc
                logger.warning(
                    "gemini_transient_error",
                    attempt=attempt,
                    error=str(exc),
                    filename=filename,
                )
                continue
            except genai_errors.ClientError as exc:
                if exc.code == _HTTP_RATE_LIMIT:
                    last_exc = exc
                    logger.warning(
                        "gemini_rate_limit",
                        attempt=attempt,
                        error=str(exc),
                        filename=filename,
                    )
                    continue
                logger.exception("gemini_api_error", error=str(exc), filename=filename)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Document extraction failed: {exc}",
                ) from exc
            except genai_errors.APIError as exc:
                logger.exception("gemini_api_error", error=str(exc), filename=filename)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Document extraction failed: {exc}",
                ) from exc

        logger.error(
            "gemini_all_retries_exhausted",
            attempts=self._settings.llm_max_retries + 1,
            filename=filename,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document extraction failed after {self._settings.llm_max_retries + 1} attempts: {last_exc}",
        )

    async def _call_api(self, pdf_bytes: bytes, filename: str) -> str:  # noqa: ARG002 — filename reserved for future logging
        """Make a single Gemini API call and return the raw text response."""
        response = await self._client.aio.models.generate_content(
            model=_GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                types.Part.from_text(text=_EXTRACT_PROMPT),
            ],
        )
        return response.text or ""
