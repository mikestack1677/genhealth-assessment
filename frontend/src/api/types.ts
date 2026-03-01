export type OrderStatus = "pending" | "processing" | "completed";

export interface Order {
  id: string;
  patient_first_name: string | null;
  patient_last_name: string | null;
  patient_dob: string | null;
  status: OrderStatus;
  notes: string | null;
  document_filename: string | null;
  extracted_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface OrderCreate {
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string;
  status?: OrderStatus;
  notes?: string;
}

export type OrderUpdate = Partial<OrderCreate>;

export interface ActivityLog {
  id: string;
  method: string;
  path: string;
  status_code: number;
  request_summary: string | null;
  order_id: string | null;
  duration_ms: number;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ExtractedPatientData {
  first_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
}

export interface DocumentExtractionResponse {
  extracted: ExtractedPatientData;
  raw_response: Record<string, unknown>;
}

export interface ApiError {
  detail: string;
}
