export type JobStatus =
  | "needs_review"
  | "open"
  | "negotiating"
  | "assigned"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "hidden";

export type AnalysisStatus =
  | "pending"
  | "parsed"
  | "needs_review"
  | "failed"
  | "verified"
  | "form_submitted";

export type SourceType = "line_group" | "liff_form" | "admin_manual" | "line_history_import" | null;
export type JobCategory = "spot" | "charter" | "regular" | "work" | "other" | null;

export type Job = {
  id: string;
  source_type: SourceType;
  source_line_message_id: string | null;
  source_group_id?: string | null;
  source_user_id?: string | null;
  source_message_id?: string | null;
  raw_text?: string | null;
  job_category: JobCategory;
  pickup_location: string | null;
  delivery_location: string | null;
  pickup_prefecture: string | null;
  pickup_city?: string | null;
  pickup_address?: string | null;
  delivery_prefecture: string | null;
  delivery_city?: string | null;
  delivery_address?: string | null;
  scheduled_date: string | null;
  scheduled_time_text: string | null;
  delivery_date: string | null;
  posted_at?: string | null;
  pickup_date?: string | null;
  pickup_time_text?: string | null;
  delivery_time_text?: string | null;
  schedule_text?: string | null;
  date_confidence?: number | null;
  date_needs_review?: boolean | null;
  recurring?: boolean | null;
  import_batch_id?: string | null;
  history_message_hash?: string | null;
  vehicle_type: string | null;
  vehicle_count: number | null;
  cargo_type: string | null;
  price: number | null;
  distance_km?: number | null;
  distance_text?: string | null;
  distance_source?: string | null;
  standard_fare_yen?: number | null;
  fare_ratio_percent?: number | null;
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
  contact_line_user_id: string | null;
  contact_display_name: string | null;
  contact_phone: string | null;
  contact_method: "phone" | "registered_phone" | "group_reply_or_admin" | "form" | null;
  contact_missing: boolean | null;
  phone_numbers: string[] | null;
  notes: string | null;
  status: JobStatus;
  analysis_status: AnalysisStatus | null;
  confidence?: number | null;
  missing_fields?: string[] | null;
  review_required: boolean | null;
  created_by_line_user_id?: string | null;
  created_by_display_name?: string | null;
  assigned_at?: string | null;
  in_progress_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
  status_updated_at?: string | null;
  status_updated_by?: string | null;
  closed_reason?: string | null;
  closed_reported_by_line_user_id?: string | null;
  closed_reported_at?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type JobFilters = {
  pickup: string;
  delivery: string;
  vehicleType: string;
  status: "" | JobStatus;
  reviewOnly: boolean;
};

export type JobStatusUpdateCandidate = {
  id: string;
  source_line_message_id: string | null;
  source_group_id: string | null;
  source_user_id: string | null;
  source_message_id: string | null;
  raw_text: string;
  update_type: string | null;
  proposed_status: JobStatus | null;
  possible_job_id: string | null;
  candidates: JobStatusUpdateCandidateJob[] | null;
  confidence: number | null;
  review_required: boolean | null;
  reason: string | null;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  applied_at: string | null;
  ignored_at: string | null;
  reported_by_line_user_id: string | null;
  reported_by_display_name: string | null;
  is_reported_by_job_owner: boolean | null;
};

export type JobStatusUpdateCandidateJob = {
  id: string;
  pickup_location: string | null;
  delivery_location: string | null;
  status: JobStatus;
  created_at: string;
};

export type LineMessage = {
  id: string;
  source_type?: string | null;
  source_group_id: string | null;
  source_user_id: string | null;
  source_display_name?: string | null;
  source_message_id: string | null;
  event_type: string | null;
  message_type: string | null;
  raw_text: string | null;
  attachment_type: string | null;
  attachment_file_name: string | null;
  attachment_message_id: string | null;
  is_unsent: boolean;
  received_at: string | null;
  posted_at?: string | null;
  history_date?: string | null;
  history_time?: string | null;
  import_batch_id?: string | null;
  history_message_hash?: string | null;
  created_at: string;
  classification_confidence: number | null;
  classification_reason: string | null;
  processed_at: string | null;
  processing_error: string | null;
};

export const jobStatusLabels: Record<JobStatus, string> = {
  needs_review: "確認待ち",
  open: "募集中",
  negotiating: "交渉中",
  assigned: "手配済",
  in_progress: "稼働中",
  completed: "完了",
  cancelled: "キャンセル",
  hidden: "非公開",
};

export const jobCategoryLabels: Record<Exclude<JobCategory, null>, string> = {
  spot: "スポット便",
  charter: "チャーター",
  regular: "定期便",
  work: "作業案件",
  other: "その他",
};
