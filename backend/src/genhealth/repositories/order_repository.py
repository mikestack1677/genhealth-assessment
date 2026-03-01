from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from genhealth.models.order import Order, OrderStatus

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from genhealth.schemas.order import OrderCreate, OrderDocumentAttach, OrderUpdate


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def paginate(self, *, page: int = 1, page_size: int = 20) -> tuple[list[Order], int]:
        """Return a page of orders and the total count."""
        offset = (page - 1) * page_size
        count_result = await self._session.execute(select(func.count()).select_from(Order))
        total = count_result.scalar_one()
        result = await self._session.execute(
            select(Order).order_by(Order.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        """Return an order by ID, or None if not found."""
        result = await self._session.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def create(self, payload: OrderCreate) -> Order:
        """Persist a new order and return it."""
        order = Order(
            patient_first_name=payload.patient_first_name,
            patient_last_name=payload.patient_last_name,
            patient_dob=payload.patient_dob,
            notes=payload.notes,
            status=OrderStatus.PENDING,
        )
        self._session.add(order)
        await self._session.flush()
        await self._session.refresh(order)
        return order

    async def update(self, order: Order, payload: OrderUpdate) -> Order:
        """Apply partial updates to an order and return it."""
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(order, field, value)
        await self._session.flush()
        await self._session.refresh(order)
        return order

    async def update_document(self, order: Order, payload: OrderDocumentAttach) -> Order:
        """Store extraction results on an order."""
        order.document_filename = payload.filename
        order.extracted_data = payload.extracted_data
        order.status = OrderStatus.COMPLETED
        if payload.patient_first_name is not None:
            order.patient_first_name = payload.patient_first_name
        if payload.patient_last_name is not None:
            order.patient_last_name = payload.patient_last_name
        if payload.patient_dob is not None:
            order.patient_dob = payload.patient_dob
        await self._session.flush()
        await self._session.refresh(order)
        return order

    async def delete(self, order: Order) -> None:
        """Delete an order."""
        await self._session.delete(order)
        await self._session.flush()
