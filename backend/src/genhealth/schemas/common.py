from __future__ import annotations

import math

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, *, items: list[T], total: int, page: int, page_size: int) -> PaginatedResponse[T]:
        """Construct a PaginatedResponse with computed page count."""
        pages = max(1, math.ceil(total / page_size)) if page_size > 0 else 1
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)
