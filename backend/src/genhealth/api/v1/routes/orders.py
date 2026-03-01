from __future__ import annotations

import uuid  # noqa: TC003 — FastAPI resolves uuid.UUID path parameters via get_type_hints() at runtime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — FastAPI resolves Annotated[AsyncSession, Depends(...)] via get_type_hints() at runtime
)

from genhealth.core.config import Settings, get_settings
from genhealth.core.database import get_session
from genhealth.schemas.common import PaginatedResponse
from genhealth.schemas.order import OrderCreate, OrderDocumentAttach, OrderResponse, OrderUpdate
from genhealth.services.document_service import DocumentService
from genhealth.services.order_service import OrderService

logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


@router.get("/orders", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[OrderResponse]:
    """List orders with pagination."""
    service = OrderService(session)
    orders, total = await service.list_orders(page=page, page_size=page_size)
    return PaginatedResponse[OrderResponse].build(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    """Create a new order."""
    async with session.begin():
        service = OrderService(session)
        order = await service.create_order(payload)
    return OrderResponse.model_validate(order)


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    """Get an order by ID."""
    service = OrderService(session)
    order = await service.get_order(order_id)
    return OrderResponse.model_validate(order)


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: uuid.UUID,
    payload: OrderUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    """Update an order by ID."""
    async with session.begin():
        service = OrderService(session)
        order = await service.update_order(order_id, payload)
    return OrderResponse.model_validate(order)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete an order by ID."""
    async with session.begin():
        service = OrderService(session)
        await service.delete_order(order_id)


@router.post("/orders/{order_id}/document", response_model=OrderResponse)
async def upload_document(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
) -> OrderResponse:
    """Upload a PDF document, extract patient data, and attach it to the order."""
    _ = settings  # available for rate-limit config; limiter applied at app level

    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    pdf_bytes = await file.read()
    filename = file.filename or "document.pdf"

    doc_service = DocumentService()
    extracted = await doc_service.extract_patient_data(pdf_bytes, filename)

    doc_payload = OrderDocumentAttach(
        filename=filename,
        extracted_data={
            "first_name": extracted.first_name,
            "last_name": extracted.last_name,
            "date_of_birth": extracted.date_of_birth.isoformat() if extracted.date_of_birth else None,
        },
        patient_first_name=extracted.first_name,
        patient_last_name=extracted.last_name,
        patient_dob=extracted.date_of_birth,
    )

    async with session.begin():
        order_service = OrderService(session)
        order = await order_service.attach_document(order_id, doc_payload)

    logger.info(
        "document_uploaded",
        order_id=str(order_id),
        filename=filename,
        extracted_first_name=extracted.first_name,
        extracted_last_name=extracted.last_name,
    )

    return OrderResponse.model_validate(order)
