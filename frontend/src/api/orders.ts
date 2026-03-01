import client from "./client";
import type { Order, OrderCreate, OrderUpdate, PaginatedResponse } from "./types";

export async function listOrders(page = 1, pageSize = 20): Promise<PaginatedResponse<Order>> {
  const response = await client.get<PaginatedResponse<Order>>("/orders", {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function getOrder(id: string): Promise<Order> {
  const response = await client.get<Order>(`/orders/${id}`);
  return response.data;
}

export async function createOrder(data: OrderCreate): Promise<Order> {
  const response = await client.post<Order>("/orders", data);
  return response.data;
}

export async function updateOrder(id: string, data: OrderUpdate): Promise<Order> {
  const response = await client.patch<Order>(`/orders/${id}`, data);
  return response.data;
}

export async function deleteOrder(id: string): Promise<void> {
  await client.delete(`/orders/${id}`);
}

export async function uploadDocument(orderId: string, file: File): Promise<Order> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await client.post<Order>(`/orders/${orderId}/document`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
