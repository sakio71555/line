import { JobCard } from "../components/JobCard";
import { JobFiltersPanel } from "../components/JobFilters";
import type { JobFilters } from "../types/job";
import { useJobs } from "../hooks/useJobs";
import { VehicleAvailabilityListPage } from "./VehicleAvailabilityListPage";

type Props = {
  filters: JobFilters;
  onFiltersChange: (filters: JobFilters) => void;
  listView: "jobs" | "vehicles";
  onListViewChange: (view: "jobs" | "vehicles") => void;
};

export function JobListPage({ filters, onFiltersChange, listView, onListViewChange }: Props) {
  const { jobs, loading, error, reload } = useJobs(filters);

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
          <JobFiltersPanel filters={filters} onChange={onFiltersChange} onRefresh={reload} />

          <section className="list-summary">
            <strong>{loading ? "読み込み中" : `${jobs.length}件`}</strong>
            <span>公開中の案件を表示しています</span>
          </section>

          {error ? <p className="notice notice-error">{error}</p> : null}

          <div className="job-list">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {!loading && jobs.length === 0 ? (
            <p className="empty-state">条件に合う案件がありません。</p>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
