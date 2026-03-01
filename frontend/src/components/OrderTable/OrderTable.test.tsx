import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Order } from "../../api/types";
import { OrderTable } from "./OrderTable";

const mockOrders: Order[] = [
  {
    id: "order-1",
    patient_first_name: "Jane",
    patient_last_name: "Doe",
    patient_dob: "1990-01-15",
    status: "pending",
    notes: null,
    document_filename: null,
    extracted_data: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "order-2",
    patient_first_name: "John",
    patient_last_name: "Smith",
    patient_dob: null,
    status: "completed",
    notes: "Some notes",
    document_filename: "doc.pdf",
    extracted_data: null,
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  },
];

describe("OrderTable", () => {
  it("renders orders with patient names", () => {
    render(
      <OrderTable orders={mockOrders} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={false} />,
    );
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("John Smith")).toBeInTheDocument();
  });

  it("renders status badges", () => {
    render(
      <OrderTable orders={mockOrders} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={false} />,
    );
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("renders empty state when no orders", () => {
    render(<OrderTable orders={[]} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={false} />);
    expect(screen.getByText("No orders found.")).toBeInTheDocument();
  });

  it("renders loading skeleton rows when isLoading", () => {
    render(<OrderTable orders={[]} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={true} />);
    const skeletons = screen.getAllByTestId("skeleton-row");
    expect(skeletons.length).toBe(3);
  });

  it("does not render empty state when loading", () => {
    render(<OrderTable orders={[]} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={true} />);
    expect(screen.queryByText("No orders found.")).not.toBeInTheDocument();
  });

  it("calls onEdit with the correct order when edit button clicked", async () => {
    const onEdit = vi.fn();
    render(<OrderTable orders={mockOrders} onEdit={onEdit} onDelete={vi.fn()} isLoading={false} />);
    await userEvent.click(screen.getByRole("button", { name: `Edit order order-1` }));
    expect(onEdit).toHaveBeenCalledWith(mockOrders[0]);
  });

  it("calls onDelete with the correct id when delete button clicked", async () => {
    const onDelete = vi.fn();
    render(
      <OrderTable orders={mockOrders} onEdit={vi.fn()} onDelete={onDelete} isLoading={false} />,
    );
    await userEvent.click(screen.getByRole("button", { name: `Delete order order-2` }));
    expect(onDelete).toHaveBeenCalledWith("order-2");
  });

  it("shows dash for missing patient name", () => {
    const orders: Order[] = [
      {
        ...mockOrders[0],
        id: "order-3",
        patient_first_name: null,
        patient_last_name: null,
      },
    ];
    render(<OrderTable orders={orders} onEdit={vi.fn()} onDelete={vi.fn()} isLoading={false} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
