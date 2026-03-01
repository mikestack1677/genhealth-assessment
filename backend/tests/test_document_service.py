"""Unit tests for DocumentService internal logic."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from genhealth.schemas.document import ExtractedPatientData
from genhealth.services.document_service import DocumentService
from genhealth.services.llm_providers.base import LLMProvider


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
    """Create a DocumentService with a mock LLMProvider."""
    mock_provider = MagicMock(spec=LLMProvider)
    return DocumentService(mock_provider)


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
# extract_patient_data — delegation to provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_patient_data_delegates_to_provider() -> None:
    """extract_patient_data validates, calls provider.extract, and parses the result."""
    mock_provider = MagicMock(spec=LLMProvider)
    raw_json = json.dumps({"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-05-20"})
    mock_provider.extract = AsyncMock(return_value=raw_json)

    service = DocumentService(mock_provider)
    pdf_bytes = _make_minimal_pdf()

    result = await service.extract_patient_data(pdf_bytes, "test.pdf")

    mock_provider.extract.assert_awaited_once_with(pdf_bytes, "test.pdf")
    assert result.first_name == "Jane"
    assert result.last_name == "Doe"
    assert result.date_of_birth == date(1990, 5, 20)


@pytest.mark.asyncio
async def test_extract_patient_data_propagates_provider_exception() -> None:
    """HTTPException raised by the provider propagates through extract_patient_data."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.extract = AsyncMock(side_effect=HTTPException(status_code=422, detail="extraction failed"))

    service = DocumentService(mock_provider)
    pdf_bytes = _make_minimal_pdf()

    with pytest.raises(HTTPException) as exc_info:
        await service.extract_patient_data(pdf_bytes, "test.pdf")

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_extract_patient_data_validates_before_calling_provider() -> None:
    """Validation failures short-circuit before provider.extract is called."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.extract = AsyncMock()

    service = DocumentService(mock_provider)
    oversized = b"x" * (11 * 1024 * 1024)

    with pytest.raises(HTTPException) as exc_info:
        await service.extract_patient_data(oversized, "big.pdf")

    assert exc_info.value.status_code == 422
    mock_provider.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_patient_data_returns_empty_on_no_json() -> None:
    """Provider returning non-JSON text results in empty ExtractedPatientData (no crash)."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.extract = AsyncMock(return_value="I cannot find patient data in this document.")

    service = DocumentService(mock_provider)
    pdf_bytes = _make_minimal_pdf()

    result = await service.extract_patient_data(pdf_bytes, "test.pdf")

    assert result == ExtractedPatientData()
