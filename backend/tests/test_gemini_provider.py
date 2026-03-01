"""Unit tests for GeminiProvider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from google.genai import errors as genai_errors

from genhealth.services.llm_providers.gemini_provider import GeminiProvider


def _server_error(code: int = 500) -> genai_errors.ServerError:
    return genai_errors.ServerError(code, {"error": {"code": code, "status": "INTERNAL", "message": "server error"}})


def _rate_limit_error() -> genai_errors.ClientError:
    return genai_errors.ClientError(
        429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota exceeded"}}
    )


def _client_error(code: int = 400) -> genai_errors.ClientError:
    return genai_errors.ClientError(
        code, {"error": {"code": code, "status": "INVALID_ARGUMENT", "message": "bad request"}}
    )


def _make_provider() -> GeminiProvider:
    """Create a GeminiProvider with a mocked genai.Client."""
    with patch("genhealth.services.llm_providers.gemini_provider.genai.Client"):
        return GeminiProvider()


# ---------------------------------------------------------------------------
# extract — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_success() -> None:
    """Provider returns raw JSON string on the first API call with no retries."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Gemma", "last_name": "Flash", "date_of_birth": "2000-01-01"})

    with patch.object(provider, "_call_api", new_callable=AsyncMock, return_value=raw):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw


# ---------------------------------------------------------------------------
# extract — retry on transient errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_retries_on_server_error() -> None:
    """Provider retries on ServerError and succeeds on the second attempt."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Retry"})

    mock_call = AsyncMock(side_effect=[_server_error(), raw])

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.gemini_provider.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw
    assert mock_call.call_count == 2


@pytest.mark.asyncio
async def test_extract_retries_on_rate_limit() -> None:
    """Provider retries on 429 ClientError (rate limit) and succeeds on the second attempt."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Retry"})

    mock_call = AsyncMock(side_effect=[_rate_limit_error(), raw])

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.gemini_provider.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw
    assert mock_call.call_count == 2


# ---------------------------------------------------------------------------
# extract — retries exhausted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_exhausted_on_server_error() -> None:
    """All retry attempts exhausted on ServerError raises HTTPException 422."""
    provider = _make_provider()

    mock_call = AsyncMock(side_effect=_server_error())

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.gemini_provider.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc_info,
    ):
        await provider.extract(b"pdf", "test.pdf")

    assert exc_info.value.status_code == 422
    assert "attempts" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_extract_exhausted_on_rate_limit() -> None:
    """All retry attempts exhausted on 429 rate limit raises HTTPException 422."""
    provider = _make_provider()

    mock_call = AsyncMock(side_effect=_rate_limit_error())

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.gemini_provider.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc_info,
    ):
        await provider.extract(b"pdf", "test.pdf")

    assert exc_info.value.status_code == 422
    assert "attempts" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# extract — non-transient API error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_api_error_no_retry_client_error() -> None:
    """Non-429 ClientError raises HTTPException 422 immediately with only one call."""
    provider = _make_provider()

    mock_call = AsyncMock(side_effect=_client_error(400))

    with (
        patch.object(provider, "_call_api", mock_call),
        pytest.raises(HTTPException) as exc_info,
    ):
        await provider.extract(b"pdf", "test.pdf")

    assert exc_info.value.status_code == 422
    assert mock_call.call_count == 1


@pytest.mark.asyncio
async def test_extract_api_error_no_retry_generic_api_error() -> None:
    """A bare APIError (not ClientError or ServerError) raises HTTPException 422 immediately."""
    provider = _make_provider()

    # A bare APIError with code 0 is not a ClientError or ServerError subclass
    bare_api_error = genai_errors.APIError(
        0, {"error": {"code": 0, "status": "UNKNOWN", "message": "unknown api error"}}
    )
    mock_call = AsyncMock(side_effect=bare_api_error)

    with (
        patch.object(provider, "_call_api", mock_call),
        pytest.raises(HTTPException) as exc_info,
    ):
        await provider.extract(b"pdf", "test.pdf")

    assert exc_info.value.status_code == 422
    assert mock_call.call_count == 1


# ---------------------------------------------------------------------------
# _call_api
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_api_sends_request_and_returns_text() -> None:
    """_call_api sends PDF bytes to Gemini and returns response.text."""
    provider = _make_provider()

    mock_response = MagicMock()
    mock_response.text = '{"first_name": "Gemma", "last_name": "Flash", "date_of_birth": "2000-01-01"}'

    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    result = await provider._call_api(b"fake-pdf-bytes", "test.pdf")

    assert result == mock_response.text
    provider._client.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_call_api_none_text_returns_empty_string() -> None:
    """_call_api returns an empty string when response.text is None."""
    provider = _make_provider()

    mock_response = MagicMock()
    mock_response.text = None

    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    result = await provider._call_api(b"fake-pdf-bytes", "test.pdf")

    assert result == ""
