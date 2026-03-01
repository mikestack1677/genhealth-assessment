import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as activityApi from "../../api/activity";
import type { ActivityLog, PaginatedResponse } from "../../api/types";
import { ActivityPage } from "./ActivityPage";

vi.mock("../../api/activity", () => ({
  listActivity: vi.fn(),
}));

const mockLog: ActivityLog = {
  id: "log-1",
  method: "GET",
  path: "/api/v1/orders",
  status_code: 200,
  request_summary: null,
  order_id: null,
  duration_ms: 25,
  timestamp: new Date(Date.now() - 10000).toISOString(),
};

const activityResponse: PaginatedResponse<ActivityLog> = {
  items: [mockLog],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
};

function renderActivityPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ActivityPage />
    </QueryClientProvider>,
  );
}

describe("ActivityPage", () => {
  beforeEach(() => {
    vi.mocked(activityApi.listActivity).mockResolvedValue(activityResponse);
  });

  it("renders the Activity heading", () => {
    renderActivityPage();
    expect(screen.getByText("Activity")).toBeInTheDocument();
  });

  it("renders the activity feed table", async () => {
    renderActivityPage();
    await waitFor(() => {
      expect(screen.getByText("GET")).toBeInTheDocument();
    });
  });

  it("renders log path", async () => {
    renderActivityPage();
    await waitFor(() => {
      expect(screen.getByText("/api/v1/orders")).toBeInTheDocument();
    });
  });

  it("renders status code", async () => {
    renderActivityPage();
    await waitFor(() => {
      expect(screen.getByText("200")).toBeInTheDocument();
    });
  });
});
