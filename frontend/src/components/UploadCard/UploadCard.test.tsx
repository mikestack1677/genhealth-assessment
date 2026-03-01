import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UploadCard } from "./UploadCard";

vi.mock("../../api/documents", () => ({
  extractDocument: vi.fn(),
}));

vi.mock("../../api/orders", () => ({
  uploadDocument: vi.fn(),
}));

function makePdfFile(name = "test.pdf", size = 1024): File {
  const blob = new Blob(["a".repeat(size)], { type: "application/pdf" });
  return new File([blob], name, { type: "application/pdf" });
}

function makeLargeFile(): File {
  const size = 11 * 1024 * 1024;
  const blob = new Blob(["a".repeat(size)], { type: "application/pdf" });
  return new File([blob], "large.pdf", { type: "application/pdf" });
}

function makeTextFile(): File {
  return new File(["hello"], "notes.txt", { type: "text/plain" });
}

describe("UploadCard", () => {
  it("renders the upload zone", () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
  });

  it("renders the browse button", () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Browse" })).toBeInTheDocument();
  });

  it("shows error for non-PDF file type", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makeTextFile(), { applyAccept: false });
    expect(screen.getByRole("alert")).toHaveTextContent("Only PDF files are accepted.");
  });

  it("shows error for file exceeding 10MB", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makeLargeFile());
    expect(screen.getByRole("alert")).toHaveTextContent("File size must not exceed 10MB.");
  });

  it("shows filename after valid PDF selected", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile("report.pdf"));
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
  });

  it("shows Upload button after valid file selected with orderId", async () => {
    render(<UploadCard orderId="order-1" onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile());
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
  });

  it("shows Extract button after valid file selected without orderId", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile());
    expect(screen.getByRole("button", { name: "Extract" })).toBeInTheDocument();
  });

  it("does not show action button before file is selected", () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Extract" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload" })).not.toBeInTheDocument();
  });

  it("calls extractDocument and shows result on standalone extract", async () => {
    const { extractDocument } = await import("../../api/documents");
    vi.mocked(extractDocument).mockResolvedValueOnce({
      extracted: { first_name: "Jane", last_name: "Doe", date_of_birth: "1990-01-15" },
      raw_response: {},
    });
    const onSuccess = vi.fn();
    render(<UploadCard onSuccess={onSuccess} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile());
    await userEvent.click(screen.getByRole("button", { name: "Extract" }));
    await waitFor(() => {
      expect(screen.getByText("Extracted Patient Data")).toBeInTheDocument();
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("calls uploadDocument when orderId is provided", async () => {
    const { uploadDocument } = await import("../../api/orders");
    const mockOrder = {
      id: "order-1",
      patient_first_name: "Jane",
      patient_last_name: "Doe",
      patient_dob: "1990-01-15",
      status: "pending" as const,
      notes: null,
      document_filename: "doc.pdf",
      extracted_data: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(uploadDocument).mockResolvedValueOnce(mockOrder);
    const onSuccess = vi.fn();
    render(<UploadCard orderId="order-1" onSuccess={onSuccess} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile());
    await userEvent.click(screen.getByRole("button", { name: "Upload" }));
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(mockOrder);
    });
  });

  it("shows error message when upload fails", async () => {
    const { extractDocument } = await import("../../api/documents");
    vi.mocked(extractDocument).mockRejectedValueOnce(new Error("Extraction failed"));
    render(<UploadCard onSuccess={vi.fn()} />);
    const input = screen.getByTestId("file-input");
    await userEvent.upload(input, makePdfFile());
    await userEvent.click(screen.getByRole("button", { name: "Extract" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Extraction failed");
    });
  });

  it("clicking Browse button does not throw", () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const browse = screen.getByRole("button", { name: "Browse" });
    fireEvent.click(browse);
    expect(browse).toBeInTheDocument();
  });

  it("handles drag-over and drag-leave without errors", () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const zone = screen.getByTestId("upload-zone");
    fireEvent.dragOver(zone);
    fireEvent.dragLeave(zone);
    expect(zone).toBeInTheDocument();
  });

  it("processes a dropped PDF file", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const zone = screen.getByTestId("upload-zone");
    const file = makePdfFile("dropped.pdf");
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText("dropped.pdf")).toBeInTheDocument();
    });
  });

  it("shows error for dropped non-PDF file", async () => {
    render(<UploadCard onSuccess={vi.fn()} />);
    const zone = screen.getByTestId("upload-zone");
    fireEvent.drop(zone, { dataTransfer: { files: [makeTextFile()] } });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Only PDF files are accepted.");
    });
  });
});
