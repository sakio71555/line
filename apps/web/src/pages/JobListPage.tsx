import { JobCard } from "../components/JobCard";
import { JobFiltersPanel } from "../components/JobFilters";
import type { JobFilters } from "../types/job";
import { useState } from "react";

import { useJobs, type JobListStatusView } from "../hooks/useJobs";
import { VehicleAvailabilityListPage } from "./VehicleAvailabilityListPage";

type Props = {
  filters: JobFilters;
  onFiltersChange: (filters: JobFilters) => void;
  listView: "jobs" | "vehicles";
  onListViewChange: (view: "jobs" | "vehicles") => void;
};

export function JobListPage({ filters, onFiltersChange, listView, onListViewChange }: Props) {
  const [statusView, setStatusView] = useState<JobListStatusView>("active");
  const { jobs, loading, error, reload } = useJobs(filters, statusView);
  const switchStatusView = (view: JobListStatusView) => {
    setStatusView(view);
    if (filters.status) {
      onFiltersChange({ ...filters, status: "" });
    }
  };

  return (
    <main className="page-shell">
      <div className="list-view-tabs" role="tablist" aria-label="一覧切り替え">
        <button
          type="button"
          className={listView === "jobs" ? "active" : ""}
          onClick={() => onListViewChange("jobs")}
        >
          案件一覧
        </button>
        <button
          type="button"
          className={listView === "vehicles" ? "active" : ""}
          onClick={() => onListViewChange("vehicles")}
        >
          空車一覧
        </button>
      </div>

      {listView === "vehicles" ? <VehicleAvailabilityListPage /> : null}

      {listView === "jobs" ? (
        <>
          <div className="list-view-tabs job-status-tabs" role="tablist" aria-label="案件ステータス切り替え">
            <button
              type="button"
              className={statusView === "active" ? "active" : ""}
              onClick={() => switchStatusView("active")}
            >
              募集中
            </button>
            <button
              type="button"
              className={statusView === "ended" ? "active" : ""}
              onClick={() => switchStatusView("ended")}
            >
              終了案件
            </button>
          </div>

          <JobFiltersPanel filters={filters} onChange={onFiltersChange} onRefresh={reload} />

          <section className="list-summary">
            <strong>{loading ? "読み込み中" : `${jobs.length}件`}</strong>
            <span>{statusView === "ended" ? "終了した案件を表示しています" : "募集中の案件を表示しています"}</span>
          </section>

          {error ? <p className="notice notice-error">{error}</p> : null}

          <div className="job-list">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {!loading && jobs.length === 0 ? (
            <p className="empty-state">
              {statusView === "ended" ? "終了案件はありません。" : "募集中の案件はありません。"}
            </p>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
