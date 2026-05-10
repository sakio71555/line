import { webEnv } from "./env";
import type { AdminJobUpdatePayload } from "./adminApi";
import type { VehicleAvailabilityItem } from "./liffApi";
import type { Job, JobCategory, JobStatus, PostingType } from "../types/job";

export type AdminConsoleFilters = {
  q: string;
  status: "" | JobStatus;
  posting_type: "" | Exclude<PostingType, null>;
  job_category: "" | Exclude<JobCategory, null>;
  vehicle_type: string;
  company_name: string;
  phone_number: string;
  created_from: string;
  created_to: string;
  deleted_only: boolean;
  open_only: boolean;
  ended_only: boolean;
};

export type AdminConsoleAuth = {
  token: string;
};

export function createEmptyAdminConsoleFilters(): AdminConsoleFilters {
  return {
    q: "",
    status: "",
    posting_type: "",
    job_category: "",
    vehicle_type: "",
    company_name: "",
    phone_number: "",
    created_from: "",
    created_to: "",
    deleted_only: false,
    open_only: false,
    ended_only: false,
  };
}

export async function fetchAdminConsoleJobs(
  auth: AdminConsoleAuth,
  filters: AdminConsoleFilters = createEmptyAdminConsoleFilters(),
): Promise<Job[]> {
  const params = new URLSearchParams({ limit: "1000" });
  appendParam(params, "q", filters.q);
  appendParam(params, "status", filters.status);
  appendParam(params, "posting_type", filters.posting_type);
  appendParam(params, "job_category", filters.job_category);
  appendParam(params, "vehicle_type", filters.vehicle_type);
  appendParam(params, "company_name", filters.company_name);
  appendParam(params, "phone_number", filters.phone_number);
  appendParam(params, "created_from", filters.created_from);
  appendParam(params, "created_to", filters.created_to);
  if (filters.deleted_only) params.set("deleted_only", "true");
  if (filters.open_only) params.set("open_only", "true");
  if (filters.ended_only) params.set("ended_only", "true");

  const data = await adminConsoleRequest<{ jobs: Job[] }>(
    `/admin-console/jobs?${params.toString()}`,
    auth,
  );
  return data.jobs;
}

export async function updateAdminConsoleJob(
  auth: AdminConsoleAuth,
  jobId: string,
  payload: AdminJobUpdatePayload,
): Promise<Job> {
  const data = await adminConsoleRequest<{ job: Job }>(`/admin-console/jobs/${jobId}`, auth, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return data.job;
}

export async function updateAdminConsoleJobStatus(
  auth: AdminConsoleAuth,
  jobId: string,
  newStatus: JobStatus,
  reason: string,
): Promise<Job> {
  const data = await adminConsoleRequest<{ job: Job }>(`/admin-console/jobs/${jobId}/status`, auth, {
    method: "POST",
    body: JSON.stringify({
      new_status: newStatus,
      reason,
      changed_by_name: "admin_console",
    }),
  });
  return data.job;
}

export async function deleteAdminConsoleJob(auth: AdminConsoleAuth, jobId: string): Promise<Job> {
  const data = await adminConsoleRequest<{ job: Job }>(`/admin-console/jobs/${jobId}/delete`, auth, {
    method: "POST",
  });
  return data.job;
}

export async function restoreAdminConsoleJob(
  auth: AdminConsoleAuth,
  jobId: string,
  restoreStatus: JobStatus = "open",
): Promise<Job> {
  const data = await adminConsoleRequest<{ job: Job }>(`/admin-console/jobs/${jobId}/restore`, auth, {
    method: "POST",
    body: JSON.stringify({
      status: restoreStatus,
      reason: "管理者による復元",
    }),
  });
  return data.job;
}

export async function fetchAdminConsoleVehicleAvailabilities(
  auth: AdminConsoleAuth,
): Promise<VehicleAvailabilityItem[]> {
  const data = await adminConsoleRequest<{ vehicle_availabilities: VehicleAvailabilityItem[] }>(
    "/admin-console/vehicle-availabilities?limit=1000",
    auth,
  );
  return data.vehicle_availabilities;
}

async function adminConsoleRequest<T>(
  path: string,
  auth: AdminConsoleAuth,
  init: RequestInit = {},
): Promise<T> {
  if (!webEnv.apiBaseUrl) {
    throw new Error("API URLが未設定です。");
  }
  if (!auth.token.trim()) {
    throw new Error("管理者パスワードまたはトークンを入力してください。");
  }

  let response: Response;
  try {
    response = await fetch(adminConsoleUrl(path), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": auth.token,
        ...init.headers,
      },
    });
  } catch {
    throw new Error("管理者APIに接続できませんでした。");
  }

  if (!response.ok) {
    const detail = await safeErrorDetail(response);
    throw new Error(adminConsoleErrorMessage(response.status, detail));
  }

  return (await response.json()) as T;
}

function adminConsoleUrl(path: string): string {
  return `${webEnv.apiBaseUrl.replace(/\/$/, "")}${path}`;
}

function appendParam(params: URLSearchParams, key: string, value: string) {
  const trimmed = value.trim();
  if (trimmed) params.set(key, trimmed);
}

async function safeErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    return typeof data.detail === "string" ? data.detail : "";
  } catch {
    return "";
  }
}

function adminConsoleErrorMessage(status: number, detail: string): string {
  if (status === 401) return "管理者認証が必要です。";
  if (status === 403) return "管理者認証に失敗しました。";
  if (status === 503) return "管理者認証設定が不足しています。";
  if (status === 400 && detail) return detail;
  return "管理者APIの通信に失敗しました。";
}
