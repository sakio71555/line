import { webEnv } from "./env";

export type LiffJobPayload = {
  posting_type: "delivery" | "other";
  job_category: "spot" | "charter" | "regular" | "work" | "driver_recruitment" | "referral_request" | "other";
  title: string | null;
  free_text: string | null;
  target_area: string | null;
  pickup_prefecture: string | null;
  pickup_city: string | null;
  pickup_address: string | null;
  delivery_prefecture: string | null;
  delivery_city: string | null;
  delivery_address: string | null;
  scheduled_date: string | null;
  scheduled_time_text: string | null;
  delivery_date: string | null;
  delivery_time_text: string | null;
  vehicle_type: string | null;
  vehicle_count: number;
  cargo_type: string | null;
  price: number | null;
  posted_fare_yen: number | null;
  tax_type: "税別" | "税込" | "不明";
  highway_fee_note: string | null;
  fee_note: string | null;
  notes: string | null;
  distance_km: number | null;
  distance_text: string | null;
  distance_source: string | null;
  standard_fare_yen: number | null;
  fare_ratio_percent: number | null;
  fare_ratio_text?: string | null;
  fare_judgement: string | null;
  fare_calc_status: string | null;
  fare_calc_note: string | null;
  fare_region: string | null;
  fare_vehicle_class: string | null;
  fare_vehicle_label: string | null;
  company_name: string;
  contact_name: string;
  phone_number: string;
  line_user_id: string | null;
  display_name: string | null;
  session_id: string | null;
};

export type LiffJobResponse = {
  job: {
    id?: string;
    [key: string]: unknown;
  };
};

export type LiffVehiclePayload = {
  prefecture: string;
  city: string;
  vehicle_type: string;
  available_from: string | null;
  company_name: string | null;
  contact_name: string | null;
  phone_number: string | null;
  notes: string | null;
  line_user_id: string | null;
};

export type CompanySearchItem = {
  company: string;
  title: string;
  name: string;
  name_roman: string;
  tel: string;
  mobile: string;
  fax: string;
  toll_free: string;
  email: string;
  postal: string;
  region: string;
  address1: string;
  branches: string;
  address3: string;
  url: string;
  line_url: string;
  notes: string;
};

export type CompanySearchResponse = {
  items: CompanySearchItem[];
  count: number;
  message?: string;
};

export type VehicleAvailabilityItem = {
  id: string;
  source_type: string | null;
  source_group_id: string | null;
  source_user_id: string | null;
  location: string | null;
  prefecture: string | null;
  vehicle_type: string | null;
  available_from: string | null;
  available_date: string | null;
  company_name: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  phone_numbers: string[] | null;
  status: string | null;
  review_required: boolean | null;
  confidence: number | null;
  notes: string | null;
  raw_text: string | null;
  posted_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type VehicleAvailabilityListResponse = {
  vehicle_availabilities: VehicleAvailabilityItem[];
};

export type DistanceMeasurePayload = {
  pickup_address: string;
  delivery_address: string;
  pickup_prefecture?: string | null;
  vehicle_type: string;
  posted_fare: string | null;
  pickup_detail_missing?: boolean;
  delivery_detail_missing?: boolean;
};

export type DistanceMeasureResult = {
  distance_km: number | null;
  distance_text: string | null;
  distance_source: string | null;
  posted_fare_yen: number | null;
  standard_fare_yen: number | null;
  fare_ratio_percent: number | null;
  fare_ratio_text: string | null;
  fare_judgement: string | null;
  fare_vehicle_class: string | null;
  fare_vehicle_label: string | null;
  fare_calc_status: string;
  fare_calc_note: string | null;
  fare_region?: string | null;
};

function apiUrl(path: string): string {
  return `${webEnv.apiBaseUrl.replace(/\/$/, "")}${path}`;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  if (!webEnv.apiBaseUrl) {
    throw new Error("API URLが未設定です。");
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("API接続に失敗しました。CORSまたはAPI URLを確認してください。");
  }

  if (!response.ok) {
    throw new Error(await buildSafeApiError(response));
  }

  return (await response.json()) as T;
}

async function getJson<T>(path: string): Promise<T> {
  if (!webEnv.apiBaseUrl) {
    throw new Error("API URLが未設定です。");
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path));
  } catch {
    throw new Error("企業検索APIに接続できませんでした。");
  }

  if (!response.ok) {
    throw new Error(await buildSafeApiError(response));
  }

  return (await response.json()) as T;
}

async function buildSafeApiError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string" && data.detail) {
      return `${data.detail} (${response.status})`;
    }
    if (isStructuredApiDetail(data.detail)) {
      const fieldText = data.detail.fields.length > 0 ? `: ${data.detail.fields.join(", ")}` : "";
      const reasonText = data.detail.reason ? `。${data.detail.reason}` : "";
      return `${data.detail.message}${reasonText}${fieldText} (${response.status})`;
    }
    if (Array.isArray(data.detail)) {
      const fields = validationFieldsFromArray(data.detail);
      const fieldText = fields.length > 0 ? `: ${fields.join(", ")}` : "";
      return `入力データの形式が正しくありません${fieldText} (${response.status})`;
    }
  } catch {
    return `APIリクエストに失敗しました。(${response.status})`;
  }
  return `APIリクエストに失敗しました。(${response.status})`;
}

function isStructuredApiDetail(detail: unknown): detail is { message: string; fields: string[]; reason?: string } {
  if (!detail || typeof detail !== "object") return false;
  const value = detail as { message?: unknown; fields?: unknown; reason?: unknown };
  return (
    typeof value.message === "string" &&
    Array.isArray(value.fields) &&
    (value.reason === undefined || typeof value.reason === "string")
  );
}

function validationFieldsFromArray(detail: unknown[]): string[] {
  const fields: string[] = [];
  for (const item of detail) {
    if (!item || typeof item !== "object") continue;
    const loc = (item as { loc?: unknown }).loc;
    if (!Array.isArray(loc)) continue;
    const field = loc.filter((part) => part !== "body").join(".");
    if (field && !fields.includes(field)) fields.push(field);
  }
  return fields;
}

export function submitLiffJob(payload: LiffJobPayload) {
  return postJson<LiffJobResponse>("/liff/jobs", payload);
}

export function measureDistance(payload: DistanceMeasurePayload) {
  return postJson<DistanceMeasureResult>("/distance/measure", payload);
}

export function submitLiffVehicleAvailability(payload: LiffVehiclePayload) {
  return postJson<{ vehicle_availability: unknown }>("/liff/vehicle-availabilities", payload);
}

export function searchCompanies(q: string, limit = 50) {
  const params = new URLSearchParams({
    q,
    limit: String(limit),
  });
  return getJson<CompanySearchResponse>(`/companies/search?${params.toString()}`);
}

export function fetchVehicleAvailabilities(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  return getJson<VehicleAvailabilityListResponse>(`/vehicle-availabilities?${params.toString()}`);
}
