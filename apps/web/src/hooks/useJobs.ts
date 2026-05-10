import { useCallback, useEffect, useState } from "react";

import { supabase } from "../lib/supabase";
import type { Job, JobFilters } from "../types/job";

const JOB_SELECT = [
  "id",
  "source_type",
  "source_line_message_id",
  "raw_text",
  "posting_type",
  "title",
  "free_text",
  "target_area",
  "job_category",
  "pickup_location",
  "delivery_location",
  "pickup_prefecture",
  "pickup_city",
  "pickup_address",
  "delivery_prefecture",
  "delivery_city",
  "delivery_address",
  "scheduled_date",
  "scheduled_time_text",
  "delivery_date",
  "posted_at",
  "pickup_date",
  "pickup_time_text",
  "delivery_time_text",
  "schedule_text",
  "date_confidence",
  "date_needs_review",
  "recurring",
  "vehicle_type",
  "vehicle_count",
  "cargo_type",
  "price",
  "posted_fare_yen",
  "distance_km",
  "distance_text",
  "distance_source",
  "standard_fare_yen",
  "fare_ratio_percent",
  "fare_ratio_text",
  "fare_judgement",
  "fare_calc_status",
  "fare_calc_note",
  "fare_region",
  "fare_vehicle_class",
  "fare_vehicle_label",
  "tax_type",
  "fee_note",
  "highway_fee_note",
  "budget_note",
  "company_name",
  "contact_name",
  "phone_number",
  "contact_line_user_id",
  "contact_display_name",
  "contact_phone",
  "contact_method",
  "contact_missing",
  "phone_numbers",
  "notes",
  "status",
  "analysis_status",
  "review_required",
  "deleted_at",
  "deleted_by_line_user_id",
  "delete_reason",
  "created_at",
  "updated_at",
].join(",");

export type JobListStatusView = "active" | "ended";

const ACTIVE_STATUSES = ["open"];
const ENDED_STATUSES = ["assigned", "closed", "completed", "cancelled"];

export function useJobs(filters: JobFilters, statusView: JobListStatusView = "active") {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    if (!supabase) {
      setJobs([]);
      setError("Supabase frontend environment variables are not configured.");
      return;
    }

    setLoading(true);
    setError(null);

    let query = supabase
      .from("jobs")
      .select(JOB_SELECT)
      .in("status", statusView === "ended" ? ENDED_STATUSES : ACTIVE_STATUSES)
      .is("deleted_at", null)
      .order("created_at", { ascending: false })
      .limit(100);

    if (filters.pickup.trim()) {
      query = query.or(
        `pickup_location.ilike.%${filters.pickup.trim()}%,pickup_prefecture.ilike.%${filters.pickup.trim()}%`,
      );
    }

    if (filters.delivery.trim()) {
      query = query.or(
        `delivery_location.ilike.%${filters.delivery.trim()}%,delivery_prefecture.ilike.%${filters.delivery.trim()}%`,
      );
    }

    if (filters.vehicleType.trim()) {
      query = query.ilike("vehicle_type", `%${filters.vehicleType.trim()}%`);
    }

    if (filters.status) {
      query = query.eq("status", filters.status);
    }

    if (filters.reviewOnly) {
      query = query.eq("review_required", true);
    }

    const { data, error: queryError } = await query;

    if (queryError) {
      setError(queryError.message);
      setJobs([]);
    } else {
      setJobs((data ?? []) as unknown as Job[]);
    }

    setLoading(false);
  }, [filters, statusView]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  return { jobs, loading, error, reload: loadJobs };
}
