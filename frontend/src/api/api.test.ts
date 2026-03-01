import { afterEach, describe, expect, it, vi } from "vitest";

const { mockGet, mockPost, mockPut, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockDelete: vi.fn(),
}));

vi.mock("./client", () => ({
  default: {
    get: mockGet,
    post: mockPost,
    put: mockPut,
    delete: mockDelete,
  },
}));

import { listActivity } from "./activity";
import { extractDocument } from "./documents";
import {
  createOrder,
  deleteOrder,
  getOrder,
  listOrders,
  updateOrder,
  uploadDocument,
} from "./orders";

afterEach(() => {
  vi.clearAllMocks();
});

const mockOrder = {
  id: "order-1",
  patient_first_name: "Jane",
  patient_last_name: "Doe",
  patient_dob: "1990-01-15",
  status: "pending" as const,
  notes: null,
  document_filename: null,
  extracted_data: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockPaginated = { items: [mockOrder], total: 1, page: 1, page_size: 20, pages: 1 };

describe("orders API", () => {
  it("listOrders calls GET /orders with correct params", async () => {
    mockGet.mockResolvedValueOnce({ data: mockPaginated });
    const result = await listOrders(2, 10);
    expect(mockGet).toHaveBeenCalledWith("/orders", { params: { page: 2, page_size: 10 } });
    expect(result).toEqual(mockPaginated);
  });

  it("listOrders uses default params", async () => {
    mockGet.mockResolvedValueOnce({ data: mockPaginated });
    await listOrders();
    expect(mockGet).toHaveBeenCalledWith("/orders", { params: { page: 1, page_size: 20 } });
  });

  it("getOrder calls GET /orders/:id", async () => {
    mockGet.mockResolvedValueOnce({ data: mockOrder });
    const result = await getOrder("order-1");
    expect(mockGet).toHaveBeenCalledWith("/orders/order-1");
    expect(result).toEqual(mockOrder);
  });

  it("createOrder calls POST /orders", async () => {
    mockPost.mockResolvedValueOnce({ data: mockOrder });
    const result = await createOrder({ patient_first_name: "Jane" });
    expect(mockPost).toHaveBeenCalledWith("/orders", { patient_first_name: "Jane" });
    expect(result).toEqual(mockOrder);
  });

  it("updateOrder calls PUT /orders/:id", async () => {
    mockPut.mockResolvedValueOnce({ data: mockOrder });
    const result = await updateOrder("order-1", { notes: "updated" });
    expect(mockPut).toHaveBeenCalledWith("/orders/order-1", { notes: "updated" });
    expect(result).toEqual(mockOrder);
  });

  it("deleteOrder calls DELETE /orders/:id", async () => {
    mockDelete.mockResolvedValueOnce({});
    await deleteOrder("order-1");
    expect(mockDelete).toHaveBeenCalledWith("/orders/order-1");
  });

  it("uploadDocument posts FormData to /orders/:id/document", async () => {
    mockPost.mockResolvedValueOnce({ data: mockOrder });
    const file = new File(["content"], "doc.pdf", { type: "application/pdf" });
    const result = await uploadDocument("order-1", file);
    expect(mockPost).toHaveBeenCalledWith("/orders/order-1/document", expect.any(FormData), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    expect(result).toEqual(mockOrder);
  });
});

describe("documents API", () => {
  it("extractDocument posts FormData to /documents/extract", async () => {
    const mockResult = {
      extracted: { first_name: "Jane", last_name: "Doe", date_of_birth: "1990-01-15" },
      raw_response: {},
    };
    mockPost.mockResolvedValueOnce({ data: mockResult });
    const file = new File(["pdf"], "test.pdf", { type: "application/pdf" });
    const result = await extractDocument(file);
    expect(mockPost).toHaveBeenCalledWith("/documents/extract", expect.any(FormData), {
      headers: { "Content-Type": "multipart/form-data" },
    });
    expect(result).toEqual(mockResult);
  });
});

describe("activity API", () => {
  it("listActivity calls GET /activity with correct params", async () => {
    const mockResponse = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockGet.mockResolvedValueOnce({ data: mockResponse });
    const result = await listActivity(1, 20);
    expect(mockGet).toHaveBeenCalledWith("/activity", { params: { page: 1, page_size: 20 } });
    expect(result).toEqual(mockResponse);
  });

  it("listActivity uses default params", async () => {
    const mockResponse = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockGet.mockResolvedValueOnce({ data: mockResponse });
    await listActivity();
    expect(mockGet).toHaveBeenCalledWith("/activity", { params: { page: 1, page_size: 20 } });
  });
});
