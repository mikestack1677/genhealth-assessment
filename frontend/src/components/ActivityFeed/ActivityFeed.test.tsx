import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ActivityLog } from "../../api/types";
import { ActivityFeed } from "./ActivityFeed";

const mockLogs: ActivityLog[] = [
  {
    id: "log-1",
    method: "GET",
    path: "/api/v1/orders",
    status_code: 200,
    request_summary: null,
    order_id: null,
    duration_ms: 42,
    timestamp: new Date(Date.now() - 30000).toISOString(),
  },
  {
    id: "log-2",
    method: "POST",
    path: "/api/v1/orders",
    status_code: 201,
    request_summary: "create order",
    order_id: "order-1",
    duration_ms: 88,
    timestamp: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: "log-3",
    method: "DELETE",
    path: "/api/v1/orders/abc",
    status_code: 404,
    request_summary: null,
    order_id: null,
    duration_ms: 15,
    timestamp: new Date(Date.now() - 3600000).toISOString(),
  },
];

describe("ActivityFeed", () => {
  it("renders log rows", () => {
    render(<ActivityFeed logs={mockLogs} isLoading={false} />);
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("POST")).toBeInTheDocument();
    expect(screen.getByText("DELETE")).toBeInTheDocument();
  });

  it("renders empty state when no logs", () => {
    render(<ActivityFeed logs={[]} isLoading={false} />);
    expect(screen.getByText("No activity yet.")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading", () => {
    render(<ActivityFeed logs={[]} isLoading={true} />);
    const skeletons = screen.getAllByTestId("skeleton-row");
    expect(skeletons.length).toBe(3);
  });

  it("renders method badges with expected text", () => {
    render(<ActivityFeed logs={mockLogs} isLoading={false} />);
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("POST")).toBeInTheDocument();
    expect(screen.getByText("DELETE")).toBeInTheDocument();
  });

  it("renders status codes", () => {
    render(<ActivityFeed logs={mockLogs} isLoading={false} />);
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByText("201")).toBeInTheDocument();
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("renders path values", () => {
    render(<ActivityFeed logs={mockLogs} isLoading={false} />);
    expect(screen.getAllByText("/api/v1/orders").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("/api/v1/orders/abc")).toBeInTheDocument();
  });

  it("renders duration in ms", () => {
    render(<ActivityFeed logs={mockLogs} isLoading={false} />);
    expect(screen.getByText("42ms")).toBeInTheDocument();
  });

  it("does not render empty state when loading", () => {
    vi.useFakeTimers();
    render(<ActivityFeed logs={[]} isLoading={true} />);
    expect(screen.queryByText("No activity yet.")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("renders PATCH/PUT method badge", () => {
    const patchLog: ActivityLog = {
      id: "log-patch",
      method: "PATCH",
      path: "/api/v1/orders/1",
      status_code: 200,
      request_summary: null,
      order_id: null,
      duration_ms: 30,
      timestamp: new Date(Date.now() - 10000).toISOString(),
    };
    render(<ActivityFeed logs={[patchLog]} isLoading={false} />);
    expect(screen.getByText("PATCH")).toBeInTheDocument();
  });

  it("renders unknown method with default badge style", () => {
    const unknownLog: ActivityLog = {
      id: "log-options",
      method: "OPTIONS",
      path: "/api/v1/health",
      status_code: 200,
      request_summary: null,
      order_id: null,
      duration_ms: 5,
      timestamp: new Date(Date.now() - 10000).toISOString(),
    };
    render(<ActivityFeed logs={[unknownLog]} isLoading={false} />);
    expect(screen.getByText("OPTIONS")).toBeInTheDocument();
  });

  it("renders days-ago timestamp for logs older than 24 hours", () => {
    const oldLog: ActivityLog = {
      id: "log-old",
      method: "GET",
      path: "/api/v1/orders",
      status_code: 200,
      request_summary: null,
      order_id: null,
      duration_ms: 20,
      timestamp: new Date(Date.now() - 2 * 24 * 3600 * 1000).toISOString(),
    };
    render(<ActivityFeed logs={[oldLog]} isLoading={false} />);
    expect(screen.getByText("2d ago")).toBeInTheDocument();
  });

  it("renders 5xx status badge", () => {
    const errorLog: ActivityLog = {
      id: "log-500",
      method: "POST",
      path: "/api/v1/orders",
      status_code: 500,
      request_summary: null,
      order_id: null,
      duration_ms: 100,
      timestamp: new Date(Date.now() - 10000).toISOString(),
    };
    render(<ActivityFeed logs={[errorLog]} isLoading={false} />);
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});
