import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as ordersApi from "../../api/orders";
import type { Order } from "../../api/types";
import { OrderDetailPage } from "./OrderDetailPage";

vi.mock("../../api/orders", () => ({
  getOrder: vi.fn(),
  updateOrder: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock("../../api/documents", () => ({
  extractDocument: vi.fn(),
}));

const mockOrder: Order = {
  id: "order-abc",
  patient_first_name: "Alice",
  patient_last_name: "Walker",
  patient_dob: "1985-03-10",
  status: "completed",
  notes: "Test notes",
  document_filename: "report.pdf",
  extracted_data: { name: "Alice Walker", dob: "1985-03-10" },
  created_at: "2026-01-01T10:00:00Z",
  updated_at: "2026-01-02T10:00:00Z",
};

const orderWithoutExtracted: Order = {
  ...mockOrder,
  extracted_data: null,
};

function renderDetailPage(orderId = "order-abc") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/orders/${orderId}`]}>
        <Routes>
          <Route path="/orders/:id" element={<OrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrderDetailPage", () => {
  beforeEach(() => {
    vi.mocked(ordersApi.getOrder).mockResolvedValue(mockOrder);
  });

  it("renders the Order Detail heading", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("Order Detail")).toBeInTheDocument();
    });
  });

  it("renders patient first name", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("Alice")).toBeInTheDocument();
    });
  });

  it("renders patient last name", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("Walker")).toBeInTheDocument();
    });
  });

  it("renders order status badge", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("completed")).toBeInTheDocument();
    });
  });

  it("shows extracted data section when order has extracted_data", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Extracted data" })).toBeInTheDocument();
    });
  });

  it("does not show extracted data section when order has no extracted_data", async () => {
    vi.mocked(ordersApi.getOrder).mockResolvedValue(orderWithoutExtracted);
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("Order Detail")).toBeInTheDocument();
    });
    expect(screen.queryByRole("region", { name: "Extracted data" })).not.toBeInTheDocument();
  });

  it("renders back link to orders", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /back to orders/i })).toBeInTheDocument();
    });
  });

  it("renders document upload section", async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText("Upload Document")).toBeInTheDocument();
    });
  });

  it("shows error when order fetch fails", async () => {
    vi.mocked(ordersApi.getOrder).mockRejectedValue(new Error("Order not found"));
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Order not found");
    });
  });

  it("shows edit form when Edit button is clicked", async () => {
    renderDetailPage();
    await waitFor(() => expect(screen.getByText("Order Detail")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("form", { name: "Order form" })).toBeInTheDocument();
  });

  it("calls updateOrder and closes form on edit submission", async () => {
    vi.mocked(ordersApi.updateOrder).mockResolvedValue(mockOrder);
    renderDetailPage();
    await waitFor(() => expect(screen.getByText("Order Detail")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    await userEvent.click(screen.getByRole("button", { name: "Update Order" }));
    await waitFor(() => {
      expect(ordersApi.updateOrder).toHaveBeenCalledWith("order-abc", expect.any(Object));
    });
    await waitFor(() => {
      expect(screen.queryByRole("form", { name: "Order form" })).not.toBeInTheDocument();
    });
  });

  it("closes edit form when cancel is clicked", async () => {
    renderDetailPage();
    await waitFor(() => expect(screen.getByText("Order Detail")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("form", { name: "Order form" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: "Order form" })).not.toBeInTheDocument();
  });
});
