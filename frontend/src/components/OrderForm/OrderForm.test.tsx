import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Order } from "../../api/types";
import { OrderForm } from "./OrderForm";

const mockOrder: Order = {
  id: "order-1",
  patient_first_name: "Jane",
  patient_last_name: "Doe",
  patient_dob: "1990-05-15",
  status: "processing",
  notes: "Existing notes",
  document_filename: null,
  extracted_data: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("OrderForm", () => {
  it("renders all fields", () => {
    render(<OrderForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />);
    expect(screen.getByLabelText("First Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Last Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Date of Birth")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toBeInTheDocument();
    expect(screen.getByLabelText("Notes")).toBeInTheDocument();
  });

  it("shows New Order title when no order provided", () => {
    render(<OrderForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />);
    expect(screen.getByText("New Order")).toBeInTheDocument();
  });

  it("shows Edit Order title when order provided", () => {
    render(
      <OrderForm order={mockOrder} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
    );
    expect(screen.getByText("Edit Order")).toBeInTheDocument();
  });

  it("pre-fills fields from existing order", () => {
    render(
      <OrderForm order={mockOrder} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
    );
    expect(screen.getByLabelText<HTMLInputElement>("First Name").value).toBe("Jane");
    expect(screen.getByLabelText<HTMLInputElement>("Last Name").value).toBe("Doe");
    expect(screen.getByLabelText<HTMLSelectElement>("Status").value).toBe("processing");
    expect(screen.getByLabelText<HTMLTextAreaElement>("Notes").value).toBe("Existing notes");
  });

  it("calls onSubmit with form data on submit", async () => {
    const onSubmit = vi.fn();
    render(<OrderForm onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />);

    await userEvent.type(screen.getByLabelText("First Name"), "Alice");
    await userEvent.type(screen.getByLabelText("Last Name"), "Walker");
    await userEvent.click(screen.getByRole("button", { name: "Create Order" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        patient_first_name: "Alice",
        patient_last_name: "Walker",
        status: "pending",
      }),
    );
  });

  it("calls onCancel when cancel is clicked", async () => {
    const onCancel = vi.fn();
    render(<OrderForm onSubmit={vi.fn()} onCancel={onCancel} isSubmitting={false} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
  });

  it("disables submit button when isSubmitting", () => {
    render(<OrderForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={true} />);
    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
  });

  it("shows Update Order button text in edit mode", () => {
    render(
      <OrderForm order={mockOrder} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
    );
    expect(screen.getByRole("button", { name: "Update Order" })).toBeInTheDocument();
  });

  it("includes dob, status, and notes when changed and submitted", async () => {
    const onSubmit = vi.fn();
    render(<OrderForm onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />);
    await userEvent.type(screen.getByLabelText("Date of Birth"), "1990-05-15");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "completed");
    await userEvent.type(screen.getByLabelText("Notes"), "My notes");
    await userEvent.click(screen.getByRole("button", { name: "Create Order" }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "completed",
        notes: "My notes",
      }),
    );
  });
});
