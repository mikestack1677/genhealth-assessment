from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from genhealth.repositories.order_repository import OrderRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from genhealth.models.order import Order
    from genhealth.schemas.order import OrderCreate, OrderDocumentAttach, OrderUpdate


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrderRepository(session)

    async def list_orders(self, *, page: int = 1, page_size: int = 20) -> tuple[list[Order], int]:
        """Return a paginated list of orders."""
        return await self._repo.paginate(page=page, page_size=page_size)

    async def get_order(self, order_id: uuid.UUID) -> Order:
        """Return an order by ID, raising 404 if not found."""
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found",
            )
        return order

    async def create_order(self, payload: OrderCreate) -> Order:
        """Create and return a new order."""
        return await self._repo.create(payload)

    async def update_order(self, order_id: uuid.UUID, payload: OrderUpdate) -> Order:
        """Update an order by ID, raising 404 if not found."""
        order = await self.get_order(order_id)
        return await self._repo.update(order, payload)

    async def delete_order(self, order_id: uuid.UUID) -> None:
        """Delete an order by ID, raising 404 if not found."""
        order = await self.get_order(order_id)
        await self._repo.delete(order)

    async def attach_document(self, order_id: uuid.UUID, payload: OrderDocumentAttach) -> Order:
        """Attach extraction results to an order."""
        order = await self.get_order(order_id)
        return await self._repo.update_document(order, payload)
