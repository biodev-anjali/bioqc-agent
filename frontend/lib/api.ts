const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ??
  "http://localhost:8000";

export type JobStatus = "pending" | "uploaded" | "parsed" | "failed";

export interface AnalysisJob {
  id: string;
  original_filename: string;
  stored_filename: string;
  file_path: string;
  file_size: number;
  content_type: string | null;
  file_type: string;
  status: JobStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface QCResult {
  id: string;
  job_id: string;
  total_sequences: number;
  sequence_length: string;
  gc_percent: number;
  per_base_quality_status: string;
  per_sequence_quality_status: string;
  adapter_content_status: string;
  overrepresented_sequences_status: string;
  created_at: string;
}

export interface UploadResponse {
  message: string;
  job: AnalysisJob;
}

export interface ParseResponse {
  message: string;
  job: AnalysisJob;
  result: QCResult;
}

interface APIErrorResponse {
  detail?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;

    try {
      const error = (await response.json()) as APIErrorResponse;
      if (error.detail) {
        message = error.detail;
      }
    } catch {
      // Keep the status-based fallback when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function uploadJobFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadResponse>("/api/jobs/upload", {
    method: "POST",
    body: formData,
  });
}

export function getJobStatus(jobId: string): Promise<AnalysisJob> {
  return request<AnalysisJob>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function parseJob(jobId: string): Promise<ParseResponse> {
  return request<ParseResponse>(
    `/api/jobs/${encodeURIComponent(jobId)}/parse`,
    { method: "POST" },
  );
}
