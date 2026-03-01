import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./api/orders", () => ({
  listOrders: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, pages: 1 }),
  createOrder: vi.fn(),
  updateOrder: vi.fn(),
  deleteOrder: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock("./api/activity", () => ({
  listActivity: vi
    .fn()
    .mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, pages: 1 }),
}));

vi.mock("./api/documents", () => ({
  extractDocument: vi.fn(),
}));

describe("App", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(screen.getByText("GenHealth")).toBeInTheDocument();
  });

  it("renders the main navigation", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: "Orders" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Activity" })).toBeInTheDocument();
  });
});
