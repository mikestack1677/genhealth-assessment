"""Unit tests for AnthropicProvider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from fastapi import HTTPException

from genhealth.services.llm_providers.anthropic_provider import AnthropicProvider


def _make_provider() -> AnthropicProvider:
    """Create an AnthropicProvider with a mocked Anthropic client."""
    with patch("genhealth.services.llm_providers.anthropic_provider.anthropic.AsyncAnthropic"):
        return AnthropicProvider()


# ---------------------------------------------------------------------------
# extract — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_success_first_attempt() -> None:
    """Provider returns raw JSON string on the first API call with no retries."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-05-20"})

    with patch.object(provider, "_call_api", new_callable=AsyncMock, return_value=raw):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw


# ---------------------------------------------------------------------------
# extract — retry on transient errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_retries_on_rate_limit() -> None:
    """Provider retries on RateLimitError and succeeds on the second attempt."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Retry"})

    mock_call = AsyncMock(
        side_effect=[
            anthropic.RateLimitError(message="rate limited", response=MagicMock(status_code=429), body={}),
            raw,
        ]
    )

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw
    assert mock_call.call_count == 2


@pytest.mark.asyncio
async def test_extract_retries_on_internal_server_error() -> None:
    """Provider retries on InternalServerError and succeeds on the second attempt."""
    provider = _make_provider()
    raw = json.dumps({"first_name": "Retry"})

    mock_call = AsyncMock(
        side_effect=[
            anthropic.InternalServerError(
                message="internal error",
                response=MagicMock(status_code=500),
                body={},
            ),
            raw,
        ]
    )

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await provider.extract(b"pdf", "test.pdf")

    assert result == raw
    assert mock_call.call_count == 2


# ---------------------------------------------------------------------------
# extract — retries exhausted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_retries_exhausted() -> None:
    """All retry attempts exhausted raises HTTPException 422."""
    provider = _make_provider()

    mock_call = AsyncMock(
        side_effect=anthropic.RateLimitError(message="rate limited", response=MagicMock(status_code=429), body={})
    )

    with (
        patch.object(provider, "_call_api", mock_call),
        patch("genhealth.services.llm_providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc_info,
    ):
        await provider.extract(b"pdf", "test.pdf")

    assert exc_info.value.status_code == 422
    assert "attempts" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# extract — non-transient API error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_api_error_no_retry() -> None:
    """Non-transient APIError raises HTTPException 422 immediately with only one call."""
    provider = _make_provider()

    mock_call = AsyncMock(
        side_effect=anthropic.APIError(
            message="bad request",
            request=MagicMock(),
            body={"error": {"type": "invalid_request_error", "message": "bad"}},
        )
    )

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
    """_call_api encodes PDF as base64, sends to Anthropic, and returns response text."""
    provider = _make_provider()

    mock_content = MagicMock()
    mock_content.text = '{"first_name": "Claude", "last_name": "Test", "date_of_birth": "2000-01-01"}'

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    provider._client.messages.create = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    result = await provider._call_api(b"fake-pdf-bytes", "test.pdf")

    assert result == mock_content.text
    provider._client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_call_api_empty_content_returns_empty_string() -> None:
    """_call_api returns an empty string when the response has no content."""
    provider = _make_provider()

    mock_response = MagicMock()
    mock_response.content = []

    provider._client.messages.create = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    result = await provider._call_api(b"fake-pdf-bytes", "test.pdf")

    assert result == ""
