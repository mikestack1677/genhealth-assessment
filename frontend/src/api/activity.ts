import client from "./client";
import type { ActivityLog, PaginatedResponse } from "./types";

export async function listActivity(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<ActivityLog>> {
  const response = await client.get<PaginatedResponse<ActivityLog>>("/activity", {
    params: { page, page_size: pageSize },
  });
  return response.data;
}
