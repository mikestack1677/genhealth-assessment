"""Unit tests for DocumentService internal logic."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from fastapi import HTTPException

from genhealth.schemas.document import ExtractedPatientData
from genhealth.services.document_service import DocumentService


def _make_minimal_pdf() -> bytes:
    """Return a minimal valid PDF byte string for testing."""
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""


def _make_service() -> DocumentService:
    """Create a DocumentService with a mocked Anthropic client."""
    with patch("genhealth.services.document_service.anthropic.AsyncAnthropic"):
        return DocumentService()


# ---------------------------------------------------------------------------
# _validate_file_size
# ---------------------------------------------------------------------------


def test_validate_file_size_within_limit() -> None:
    """Files within the size limit pass validation without raising."""
    service = _make_service()
    small_bytes = b"x" * 1024  # 1 KB
    service._validate_file_size(small_bytes, "test.pdf")


def test_validate_file_size_exceeds_limit() -> None:
    """Files exceeding the size limit raise HTTPException 422."""
    service = _make_service()
    large_bytes = b"x" * (11 * 1024 * 1024)  # 11 MB, default max is 10 MB
    with pytest.raises(HTTPException) as exc_info:
        service._validate_file_size(large_bytes, "big.pdf")
    assert exc_info.value.status_code == 422
    assert "exceeds maximum" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# _validate_page_count
# ---------------------------------------------------------------------------


def test_validate_page_count_valid_pdf() -> None:
    """Single-page PDF passes page count validation."""
    service = _make_service()
    pdf_bytes = _make_minimal_pdf()
    service._validate_page_count(pdf_bytes, "test.pdf")


def test_validate_page_count_invalid_pdf() -> None:
    """Non-PDF bytes raise HTTPException 422 with readable error."""
    service = _make_service()
    with pytest.raises(HTTPException) as exc_info:
        service._validate_page_count(b"not a pdf", "bad.pdf")
    assert exc_info.value.status_code == 422
    assert "could not read pdf" in exc_info.value.detail.lower()


def test_validate_page_count_too_many_pages() -> None:
    """PDFs exceeding the page limit raise HTTPException 422."""
    service = _make_service()
    with patch("genhealth.services.document_service.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()] * 25
        mock_reader_cls.return_value = mock_reader
        with pytest.raises(HTTPException) as exc_info:
            service._validate_page_count(b"fake", "long.pdf")
    assert exc_info.value.status_code == 422
    assert "25 pages" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


def test_parse_response_full_json() -> None:
    """Valid JSON with all fields is parsed correctly."""
    service = _make_service()
    raw = json.dumps({"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-05-20"})
    result = service._parse_response(raw, "test.pdf")
    assert result.first_name == "Jane"
    assert result.last_name == "Doe"
    assert result.date_of_birth == date(1990, 5, 20)


def test_parse_response_null_fields() -> None:
    """JSON with null values returns ExtractedPatientData with None fields."""
    service = _make_service()
    raw = json.dumps({"first_name": None, "last_name": None, "date_of_birth": None})
    result = service._parse_response(raw, "test.pdf")
    assert result.first_name is None
    assert result.last_name is None
    assert result.date_of_birth is None


def test_parse_response_wrapped_in_markdown() -> None:
    """JSON wrapped in markdown code fences is extracted correctly."""
    service = _make_service()
    raw = '```json\n{"first_name": "Alice", "last_name": "Smith", "date_of_birth": "1985-12-01"}\n```'
    result = service._parse_response(raw, "test.pdf")
    assert result.first_name == "Alice"
    assert result.last_name == "Smith"


def test_parse_response_no_json_found() -> None:
    """Response with no JSON returns empty ExtractedPatientData."""
    service = _make_service()
    result = service._parse_response("Sorry, I could not find any patient data.", "test.pdf")
    assert result.first_name is None
    assert result.last_name is None
    assert result.date_of_birth is None


def test_parse_response_invalid_json() -> None:
    """Malformed JSON returns empty ExtractedPatientData."""
    service = _make_service()
    result = service._parse_response("{invalid json}", "test.pdf")
    assert result.first_name is None
    assert result.last_name is None


def test_parse_response_partial_fields() -> None:
    """JSON with only some fields populates what is present."""
    service = _make_service()
    raw = json.dumps({"first_name": "Bob"})
    result = service._parse_response(raw, "test.pdf")
    assert result.first_name == "Bob"
    assert result.last_name is None
    assert result.date_of_birth is None


# ---------------------------------------------------------------------------
# _call_claude_with_retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_claude_with_retry_success_first_attempt() -> None:
    """Claude succeeds on first attempt with no retries."""
    service = _make_service()
    expected = ExtractedPatientData(first_name="Jane", last_name="Doe")
    with patch.object(service, "_call_claude", new_callable=AsyncMock, return_value=expected):
        result = await service._call_claude_with_retry(b"pdf", "test.pdf")
    assert result.first_name == "Jane"


@pytest.mark.asyncio
async def test_call_claude_with_retry_on_rate_limit() -> None:
    """Claude retries on RateLimitError and succeeds on second attempt."""
    service = _make_service()
    expected = ExtractedPatientData(first_name="Retry")
    mock_call = AsyncMock(
        side_effect=[
            anthropic.RateLimitError(message="rate limited", response=MagicMock(status_code=429), body={}),
            expected,
        ]
    )
    with (
        patch.object(service, "_call_claude", mock_call),
        patch("genhealth.services.document_service.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await service._call_claude_with_retry(b"pdf", "test.pdf")
    assert result.first_name == "Retry"
    assert mock_call.call_count == 2


@pytest.mark.asyncio
async def test_call_claude_with_retry_exhausted() -> None:
    """All retry attempts exhausted raises HTTPException 422."""
    service = _make_service()
    mock_call = AsyncMock(
        side_effect=anthropic.RateLimitError(message="rate limited", response=MagicMock(status_code=429), body={})
    )
    with (
        patch.object(service, "_call_claude", mock_call),
        patch("genhealth.services.document_service.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service._call_claude_with_retry(b"pdf", "test.pdf")
    assert exc_info.value.status_code == 422
    assert "attempts" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_call_claude_with_retry_api_error_no_retry() -> None:
    """Non-transient APIError raises HTTPException immediately without retry."""
    service = _make_service()
    mock_call = AsyncMock(
        side_effect=anthropic.APIError(
            message="bad request",
            request=MagicMock(),
            body={"error": {"type": "invalid_request_error", "message": "bad"}},
        )
    )
    with (
        patch.object(service, "_call_claude", mock_call),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service._call_claude_with_retry(b"pdf", "test.pdf")
    assert exc_info.value.status_code == 422
    assert mock_call.call_count == 1


# ---------------------------------------------------------------------------
# _call_claude
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_claude_sends_request_and_parses() -> None:
    """_call_claude sends a request to Anthropic and parses the response."""
    service = _make_service()

    mock_content = MagicMock()
    mock_content.text = '{"first_name": "Claude", "last_name": "Test", "date_of_birth": "2000-01-01"}'

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    service._client.messages.create = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    pdf_bytes = _make_minimal_pdf()
    result = await service._call_claude(pdf_bytes, "test.pdf")

    assert result.first_name == "Claude"
    assert result.last_name == "Test"
    assert result.date_of_birth == date(2000, 1, 1)
    service._client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_call_claude_empty_content() -> None:
    """_call_claude handles empty response content gracefully."""
    service = _make_service()

    mock_response = MagicMock()
    mock_response.content = []

    service._client.messages.create = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    result = await service._call_claude(b"pdf", "test.pdf")
    assert result.first_name is None
    assert result.last_name is None
