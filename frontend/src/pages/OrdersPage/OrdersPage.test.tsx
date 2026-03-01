import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as ordersApi from "../../api/orders";
import type { Order, PaginatedResponse } from "../../api/types";
import { OrdersPage } from "./OrdersPage";

vi.mock("../../api/orders", () => ({
  listOrders: vi.fn(),
  createOrder: vi.fn(),
  updateOrder: vi.fn(),
  deleteOrder: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock("../../api/documents", () => ({
  extractDocument: vi.fn(),
}));

// Stub UploadCard so tests can trigger onSuccess directly without real file I/O
vi.mock("../../components/UploadCard/UploadCard", () => ({
  UploadCard: ({ onSuccess }: { onSuccess: (result: unknown) => void }) => (
    <div data-testid="upload-zone">
      <button
        type="button"
        onClick={() =>
          onSuccess({ first_name: "Alice", last_name: "Smith", date_of_birth: "1990-05-20" })
        }
      >
        Simulate Extraction
      </button>
      <button
        type="button"
        onClick={() =>
          onSuccess({
            id: "order-9",
            patient_first_name: "Bob",
            patient_last_name: "Ross",
            patient_dob: null,
            status: "pending",
            notes: null,
            document_filename: "doc.pdf",
            extracted_data: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          })
        }
      >
        Simulate Order Upload
      </button>
    </div>
  ),
}));

const mockOrder: Order = {
  id: "order-1",
  patient_first_name: "Jane",
  patient_last_name: "Doe",
  patient_dob: "1990-01-01",
  status: "pending",
  notes: null,
  document_filename: null,
  extracted_data: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const emptyResponse: PaginatedResponse<Order> = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  pages: 1,
};

const pageResponse: PaginatedResponse<Order> = {
  items: [mockOrder],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
};

function renderOrdersPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OrdersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrdersPage", () => {
  beforeEach(() => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(pageResponse);
    vi.mocked(ordersApi.createOrder).mockResolvedValue(mockOrder);
  });

  it("renders the Orders heading", () => {
    renderOrdersPage();
    expect(screen.getByText("Orders")).toBeInTheDocument();
  });

  it("renders New Order button", () => {
    renderOrdersPage();
    expect(screen.getByRole("button", { name: "New Order" })).toBeInTheDocument();
  });

  it("displays orders from the API", async () => {
    renderOrdersPage();
    await waitFor(() => {
      expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    });
  });

  it("shows the order form when New Order is clicked", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "New Order" }));
    expect(screen.getByRole("form", { name: "Order form" })).toBeInTheDocument();
  });

  it("calls createOrder when form is submitted", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "New Order" }));
    await userEvent.type(screen.getByLabelText("First Name"), "Alice");
    await userEvent.type(screen.getByLabelText("Last Name"), "Walker");
    await userEvent.click(screen.getByRole("button", { name: "Create Order" }));
    await waitFor(() => {
      expect(ordersApi.createOrder).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_first_name: "Alice",
          patient_last_name: "Walker",
        }),
      );
    });
  });

  it("shows error message when createOrder fails", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    vi.mocked(ordersApi.createOrder).mockRejectedValue(new Error("Server error"));
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "New Order" }));
    await userEvent.type(screen.getByLabelText("First Name"), "Alice");
    await userEvent.click(screen.getByRole("button", { name: "Create Order" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Server error");
    });
  });

  it("hides form when cancel is clicked", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "New Order" }));
    expect(screen.getByRole("form", { name: "Order form" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: "Order form" })).not.toBeInTheDocument();
  });

  it("toggles upload section visibility", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    renderOrdersPage();
    expect(screen.queryByTestId("upload-zone")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Extract from PDF" }));
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
  });

  it("auto-creates order and hides upload when extraction succeeds", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "Extract from PDF" }));
    await userEvent.click(screen.getByRole("button", { name: "Simulate Extraction" }));
    await waitFor(() => {
      expect(ordersApi.createOrder).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_first_name: "Alice",
          patient_last_name: "Smith",
          patient_dob: "1990-05-20",
          status: "pending",
        }),
      );
    });
    expect(screen.queryByTestId("upload-zone")).not.toBeInTheDocument();
  });

  it("does not create order when upload result has no patient data", async () => {
    vi.mocked(ordersApi.listOrders).mockResolvedValue(emptyResponse);
    vi.mocked(ordersApi.createOrder).mockClear();
    renderOrdersPage();
    await userEvent.click(screen.getByRole("button", { name: "Extract from PDF" }));
    await userEvent.click(screen.getByRole("button", { name: "Simulate Order Upload" }));
    expect(ordersApi.createOrder).not.toHaveBeenCalled();
  });

  it("opens edit form when edit button clicked", async () => {
    renderOrdersPage();
    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit order order-1" }));
    expect(screen.getByRole("form", { name: "Order form" })).toBeInTheDocument();
  });

  it("calls updateOrder when editing an existing order", async () => {
    vi.mocked(ordersApi.updateOrder).mockResolvedValue(mockOrder);
    renderOrdersPage();
    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit order order-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Update Order" }));
    await waitFor(() => {
      expect(ordersApi.updateOrder).toHaveBeenCalledWith("order-1", expect.any(Object));
    });
  });

  it("shows error message when updateOrder fails", async () => {
    vi.mocked(ordersApi.updateOrder).mockRejectedValue(new Error("Update failed"));
    renderOrdersPage();
    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Edit order order-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Update Order" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Update failed");
    });
  });

  it("calls deleteOrder when delete button clicked", async () => {
    vi.mocked(ordersApi.deleteOrder).mockResolvedValue(undefined);
    renderOrdersPage();
    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Delete order order-1" }));
    await waitFor(() => {
      expect(ordersApi.deleteOrder).toHaveBeenCalledWith("order-1");
    });
  });

  it("shows error message when deleteOrder fails", async () => {
    vi.mocked(ordersApi.deleteOrder).mockRejectedValue(new Error("Delete failed"));
    renderOrdersPage();
    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Delete order order-1" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Delete failed");
    });
  });
});
