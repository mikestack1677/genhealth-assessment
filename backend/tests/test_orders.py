from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient) -> None:
    """POST /orders creates a new order and returns 201."""
    payload = {
        "patient_first_name": "Alice",
        "patient_last_name": "Smith",
        "patient_dob": "1990-03-15",
        "notes": "Initial consultation",
    }
    response = await client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_first_name"] == "Alice"
    assert data["patient_last_name"] == "Smith"
    assert data["patient_dob"] == "1990-03-15"
    assert data["status"] == "pending"
    assert data["notes"] == "Initial consultation"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_order_minimal(client: AsyncClient) -> None:
    """POST /orders succeeds with no fields set."""
    response = await client.post("/api/v1/orders", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["patient_first_name"] is None
    assert data["patient_last_name"] is None


@pytest.mark.asyncio
async def test_get_order(client: AsyncClient) -> None:
    """GET /orders/{id} returns the order."""
    create_resp = await client.post(
        "/api/v1/orders",
        json={"patient_first_name": "Jane", "patient_last_name": "Doe"},
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/orders/{order_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["patient_first_name"] == "Jane"
    assert data["patient_last_name"] == "Doe"


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient) -> None:
    """GET /orders/{id} returns 404 for unknown ID."""
    missing_id = uuid.uuid4()
    response = await client.get(f"/api/v1/orders/{missing_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient) -> None:
    """GET /orders returns a paginated response with created orders."""
    create_resp = await client.post("/api/v1/orders", json={"patient_first_name": "Listed"})
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    response = await client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert order_id in ids


@pytest.mark.asyncio
async def test_list_orders_pagination(client: AsyncClient) -> None:
    """GET /orders respects page and page_size parameters."""
    # Create two orders
    await client.post("/api/v1/orders", json={"patient_first_name": "Page1"})
    await client.post("/api/v1/orders", json={"patient_first_name": "Page2"})

    response = await client.get("/api/v1/orders?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_update_order(client: AsyncClient) -> None:
    """PUT /orders/{id} updates partial fields."""
    create_resp = await client.post(
        "/api/v1/orders",
        json={"patient_first_name": "Original", "patient_last_name": "Name"},
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]
    original_last_name = create_resp.json()["patient_last_name"]

    payload = {"patient_first_name": "Updated", "notes": "Changed note"}
    response = await client.put(f"/api/v1/orders/{order_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_first_name"] == "Updated"
    assert data["notes"] == "Changed note"
    # Fields not in payload remain unchanged
    assert data["patient_last_name"] == original_last_name


@pytest.mark.asyncio
async def test_update_order_status(client: AsyncClient) -> None:
    """PUT /orders/{id} can update the status field."""
    create_resp = await client.post("/api/v1/orders", json={})
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    payload = {"status": "processing"}
    response = await client.put(f"/api/v1/orders/{order_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_update_order_not_found(client: AsyncClient) -> None:
    """PUT /orders/{id} returns 404 for unknown ID."""
    missing_id = uuid.uuid4()
    response = await client.put(f"/api/v1/orders/{missing_id}", json={"notes": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_order(client: AsyncClient) -> None:
    """DELETE /orders/{id} returns 204 and order is gone."""
    create_resp = await client.post("/api/v1/orders", json={"patient_first_name": "ToDelete"})
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/orders/{order_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_order_not_found(client: AsyncClient) -> None:
    """DELETE /orders/{id} returns 404 for unknown ID."""
    missing_id = uuid.uuid4()
    response = await client.delete(f"/api/v1/orders/{missing_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_order_response_shape(client: AsyncClient) -> None:
    """Order response contains all expected fields."""
    response = await client.post(
        "/api/v1/orders",
        json={"patient_first_name": "Bob", "patient_last_name": "Jones", "patient_dob": "1975-12-01"},
    )
    assert response.status_code == 201
    data = response.json()
    expected_fields = {
        "id",
        "patient_first_name",
        "patient_last_name",
        "patient_dob",
        "status",
        "notes",
        "document_filename",
        "extracted_data",
        "created_at",
        "updated_at",
    }
    assert expected_fields.issubset(data.keys())
