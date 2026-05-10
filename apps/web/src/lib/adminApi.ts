import { webEnv } from "./env";
import type { Job, JobStatus, JobStatusUpdateCandidate, LineMessage } from "../types/job";

export type AdminJobScope = "all" | "mine";
export type AdminAuthContext = {
  idToken?: string | null;
};

export type AdminJobUpdatePayload = {
  posting_type?: Job["posting_type"];
  job_category: Job["job_category"];
  title?: string | null;
  free_text?: string | null;
  target_area?: string | null;
  pickup_location: string | null;
  delivery_location: string | null;
  pickup_prefecture: string | null;
  pickup_city: string | null;
  pickup_address: string | null;
  delivery_prefecture: string | null;
  delivery_city: string | null;
  delivery_address: string | null;
  pickup_date: string | null;
  pickup_time_text: string | null;
  scheduled_date: string | null;
  scheduled_time_text: string | null;
  delivery_date: string | null;
  delivery_time_text: string | null;
  vehicle_type: string | null;
  vehicle_count: number | null;
  cargo_type: string | null;
  price: number | null;
  posted_fare_yen?: number | null;
  distance_km?: number | null;
  distance_text?: string | null;
  distance_source?: string | null;
  standard_fare_yen?: number | null;
  fare_ratio_percent?: number | null;
  fare_ratio_text?: string | null;
  fare_judgement?: string | null;
  fare_calc_status?: string | null;
  fare_calc_note?: string | null;
  fare_region?: string | null;
  fare_vehicle_class?: string | null;
  fare_vehicle_label?: string | null;
  tax_type: "税別" | "税込" | "不明" | null;
  fee_note: string | null;
  highway_fee_note: string | null;
  budget_note: string | null;
  company_name: string | null;
  contact_name: string | null;
  phone_number: string | null;
  phone_numbers: string[] | null;
  notes: string | null;
};

function adminUrl(path: string): string {
  return `${webEnv.apiBaseUrl.replace(/\/$/, "")}${path}`;
}

async function requestJson<T>(
  input: string,
  init?: RequestInit,
  meta?: { endpoint: string; scope?: AdminJobScope; jobId?: string },
): Promise<T> {
  if (!webEnv.apiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const response = await fetch(input, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const message = await safeAdminErrorMessage(response);
    console.warn("Admin API request failed", {
      endpoint: meta?.endpoint ?? input,
      status: response.status,
      hasAuthorization: hasAuthorization(init?.headers),
      scope: meta?.scope ?? "mine",
      jobId: meta?.jobId,
      message,
    });
    throw new Error(adminErrorMessage(response.status, message));
  }

  return (await response.json()) as T;
}

export async function fetchAdminJobs(idToken?: string | null): Promise<Job[]> {
  const context = { idToken };
  const headers = adminAuthHeaders(context);

  const data = await requestJson<{ jobs: Job[] }>(
    adminUrl(withAdminScope("/admin/jobs")),
    { headers },
    { endpoint: "/admin/jobs", scope: "mine" },
  );
  return data.jobs;
}

export async function updateAdminJob(
  jobId: string,
  payload: AdminJobUpdatePayload,
  context: AdminAuthContext = {},
): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "PATCH",
      headers: adminAuthHeaders(context),
      body: JSON.stringify(payload),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function verifyAdminJob(jobId: string, context: AdminAuthContext = {}): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}/verify`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function hideAdminJob(jobId: string, context: AdminAuthContext = {}): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}/hide`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function closeAdminJob(jobId: string, context: AdminAuthContext = {}): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}/close`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function arrangeAdminJob(jobId: string, context: AdminAuthContext = {}): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}/arrange`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function deleteAdminJob(jobId: string, context: AdminAuthContext = {}): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "DELETE",
      headers: adminAuthHeaders(context),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function updateAdminJobStatus(
  jobId: string,
  payload: {
    new_status: JobStatus;
    reason?: string | null;
    changed_by_name?: string | null;
  },
  context: AdminAuthContext = {},
): Promise<Job> {
  const endpoint = `/admin/jobs/${jobId}/status`;
  const data = await requestJson<{ job: Job }>(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
      body: JSON.stringify(payload),
    },
    { endpoint, scope: "mine", jobId },
  );
  return data.job;
}

export async function fetchStatusUpdateCandidates(context: AdminAuthContext = {}): Promise<JobStatusUpdateCandidate[]> {
  const endpoint = "/admin/status-updates";
  const data = await requestJson<{ status_updates: JobStatusUpdateCandidate[] }>(
    adminUrl(withAdminScope(endpoint)),
    { headers: adminAuthHeaders(context) },
    { endpoint, scope: "mine" },
  );
  return data.status_updates;
}

export async function fetchAdminLineMessages(): Promise<LineMessage[]> {
  const data = await requestJson<{ line_messages: LineMessage[] }>(
    adminUrl("/admin/line-messages"),
  );
  return data.line_messages;
}

export async function applyStatusUpdateCandidate(
  statusUpdateId: string,
  payload: {
    job_id?: string | null;
    new_status: "assigned" | "completed" | "cancelled";
    reason?: string | null;
    changed_by_name?: string | null;
  },
  context: AdminAuthContext = {},
): Promise<{ job: Job; status_update: JobStatusUpdateCandidate }> {
  const endpoint = `/admin/status-updates/${statusUpdateId}/apply`;
  return requestJson(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
      body: JSON.stringify(payload),
    },
    { endpoint, scope: "mine", jobId: payload.job_id ?? undefined },
  );
}

export async function ignoreStatusUpdateCandidate(
  statusUpdateId: string,
  payload: { reviewed_by?: string | null },
  context: AdminAuthContext = {},
): Promise<{ status_update: JobStatusUpdateCandidate }> {
  const endpoint = `/admin/status-updates/${statusUpdateId}/ignore`;
  return requestJson(
    adminUrl(withAdminScope(endpoint)),
    {
      method: "POST",
      headers: adminAuthHeaders(context),
      body: JSON.stringify(payload),
    },
    { endpoint, scope: "mine" },
  );
}

function adminAuthHeaders(context: AdminAuthContext): Record<string, string> {
  if (!context.idToken) {
    throw new Error("管理画面はLINE内で開いてください");
  }
  return { Authorization: `Bearer ${context.idToken}` };
}

function withAdminScope(path: string): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}scope=mine`;
}

function hasAuthorization(headers?: HeadersInit): boolean {
  if (!headers) return false;
  if (headers instanceof Headers) return headers.has("Authorization");
  if (Array.isArray(headers)) {
    return headers.some(([key]) => key.toLowerCase() === "authorization");
  }
  return Object.keys(headers).some((key) => key.toLowerCase() === "authorization");
}

async function safeAdminErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    return "";
  }
  return "";
}

function adminErrorMessage(status: number, detail: string): string {
  if (status === 401) return "LINE内で開き直してください";
  if (status === 403) return "権限がありません";
  if (status === 400 && detail) return detail;
  if (status >= 500) return "API接続に失敗しました";
  return "管理APIの通信に失敗しました";
}
