from __future__ import annotations

import asyncio
import base64

import anthropic
import structlog
from fastapi import HTTPException, status

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


class AnthropicProvider(LLMProvider):
    """LLM provider backed by Anthropic Claude."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    async def extract(self, pdf_bytes: bytes, filename: str) -> str:
        """Send PDF to Claude with exponential backoff retry on transient errors.

        Returns the raw text response expected to contain JSON.
        Raises HTTPException(422) on non-transient errors or exhausted retries.
        """
        last_exc: Exception | None = None
        for attempt in range(self._settings.llm_max_retries + 1):
            if attempt > 0:
                backoff = 2**attempt
                logger.warning(
                    "anthropic_retry",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    filename=filename,
                )
                await asyncio.sleep(backoff)
            try:
                return await self._call_api(pdf_bytes, filename)
            except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
                last_exc = exc
                logger.warning(
                    "anthropic_transient_error",
                    attempt=attempt,
                    error=str(exc),
                    filename=filename,
                )
                continue
            except anthropic.APIError as exc:
                logger.exception("anthropic_api_error", error=str(exc), filename=filename)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Document extraction failed: {exc}",
                ) from exc

        logger.error(
            "anthropic_all_retries_exhausted",
            attempts=self._settings.llm_max_retries + 1,
            filename=filename,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document extraction failed after {self._settings.llm_max_retries + 1} attempts: {last_exc}",
        )

    async def _call_api(self, pdf_bytes: bytes, filename: str) -> str:  # noqa: ARG002 — filename reserved for future logging
        """Make a single Claude API call and return the raw text response."""
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

        return response.content[0].text if response.content else ""  # type: ignore[union-attr]
