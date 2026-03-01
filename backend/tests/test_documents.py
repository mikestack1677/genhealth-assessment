from __future__ import annotations

import io
import uuid
from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from genhealth.schemas.document import ExtractedPatientData

if TYPE_CHECKING:
    from httpx import AsyncClient


def _make_minimal_pdf() -> bytes:
    """Return a minimal valid PDF byte string for testing."""
    # Minimal single-page PDF
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


@pytest.mark.asyncio
async def test_extract_document_success(client: AsyncClient) -> None:
    """POST /documents/extract returns extracted data on success."""
    extracted = ExtractedPatientData(
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1990, 5, 20),
    )

    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        return_value=extracted,
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            "/api/v1/documents/extract",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["extracted"]["first_name"] == "Jane"
    assert data["extracted"]["last_name"] == "Doe"
    assert data["extracted"]["date_of_birth"] == "1990-05-20"


@pytest.mark.asyncio
async def test_extract_document_partial_result(client: AsyncClient) -> None:
    """POST /documents/extract handles partial extraction gracefully."""
    extracted = ExtractedPatientData(first_name="John", last_name=None, date_of_birth=None)

    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        return_value=extracted,
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            "/api/v1/documents/extract",
            files={"file": ("partial.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["extracted"]["first_name"] == "John"
    assert data["extracted"]["last_name"] is None
    assert data["extracted"]["date_of_birth"] is None


@pytest.mark.asyncio
async def test_extract_document_wrong_content_type(client: AsyncClient) -> None:
    """POST /documents/extract rejects non-PDF files."""
    response = await client.post(
        "/api/v1/documents/extract",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_document_file_too_large(client: AsyncClient) -> None:
    """POST /documents/extract returns 422 when file exceeds size limit."""
    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=422, detail="File exceeds maximum allowed size"),
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            "/api/v1/documents/extract",
            files={"file": ("big.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 422
    assert "size" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_document_too_many_pages(client: AsyncClient) -> None:
    """POST /documents/extract returns 422 when page count exceeds limit."""
    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=422, detail="PDF has 25 pages, exceeding the maximum of 20"),
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            "/api/v1/documents/extract",
            files={"file": ("long.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 422
    assert "pages" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_document_llm_error(client: AsyncClient) -> None:
    """POST /documents/extract returns 422 on LLM API error."""
    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=422, detail="Document extraction failed: API error"),
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            "/api/v1/documents/extract",
            files={"file": ("error.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_order_document_upload_success(client: AsyncClient) -> None:
    """POST /orders/{id}/document extracts and attaches document to order."""
    # Create an order first
    create_resp = await client.post("/api/v1/orders", json={"patient_first_name": "Pre"})
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    extracted = ExtractedPatientData(
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1985, 3, 10),
    )

    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        return_value=extracted,
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            f"/api/v1/orders/{order_id}/document",
            files={"file": ("record.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["document_filename"] == "record.pdf"
    assert data["patient_first_name"] == "Jane"
    assert data["patient_last_name"] == "Doe"
    assert data["extracted_data"] is not None


@pytest.mark.asyncio
async def test_order_document_upload_not_found(client: AsyncClient) -> None:
    """POST /orders/{id}/document returns 404 for unknown order."""
    missing_id = uuid.uuid4()
    extracted = ExtractedPatientData()

    with patch(
        "genhealth.services.document_service.DocumentService.extract_patient_data",
        new_callable=AsyncMock,
        return_value=extracted,
    ):
        pdf_bytes = _make_minimal_pdf()
        response = await client.post(
            f"/api/v1/orders/{missing_id}/document",
            files={"file": ("x.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 404
