import { RefreshCw } from "lucide-react";

import { jobStatusLabels, type JobFilters, type JobStatus } from "../types/job";

type Props = {
  filters: JobFilters;
  onChange: (filters: JobFilters) => void;
  onRefresh: () => void;
};

const statuses: JobStatus[] = [
  "open",
  "negotiating",
  "assigned",
  "in_progress",
];

export function JobFiltersPanel({ filters, onChange, onRefresh }: Props) {
  return (
    <section className="filters" aria-label="案件検索条件">
      <div className="filters__grid">
        <label>
          <span>出発地</span>
          <input
            value={filters.pickup}
            onChange={(event) => onChange({ ...filters, pickup: event.target.value })}
            placeholder="東京、港区など"
          />
        </label>
        <label>
          <span>到着地</span>
          <input
            value={filters.delivery}
            onChange={(event) => onChange({ ...filters, delivery: event.target.value })}
            placeholder="大阪、福岡など"
          />
        </label>
        <label>
          <span>車種</span>
          <input
            value={filters.vehicleType}
            onChange={(event) => onChange({ ...filters, vehicleType: event.target.value })}
            placeholder="4t、冷凍車など"
          />
        </label>
        <label>
          <span>ステータス</span>
          <select
            value={filters.status}
            onChange={(event) =>
              onChange({ ...filters, status: event.target.value as JobFilters["status"] })
            }
          >
            <option value="">すべて</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {jobStatusLabels[status]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="filters__actions">
        <label className="toggle">
          <input
            type="checkbox"
            checked={filters.reviewOnly}
            onChange={(event) => onChange({ ...filters, reviewOnly: event.target.checked })}
          />
          <span>確認待ちのみ</span>
        </label>
        <button type="button" onClick={onRefresh}>
          <RefreshCw aria-hidden="true" size={16} strokeWidth={2.5} />
          更新
        </button>
      </div>
    </section>
  );
}
