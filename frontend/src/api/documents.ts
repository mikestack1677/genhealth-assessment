import client from "./client";
import type { DocumentExtractionResponse } from "./types";

export async function extractDocument(file: File): Promise<DocumentExtractionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await client.post<DocumentExtractionResponse>("/documents/extract", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
