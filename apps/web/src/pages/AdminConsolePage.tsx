import { RefreshCw, Search } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  createEmptyAdminConsoleFilters,
  deleteAdminConsoleJob,
  fetchAdminConsoleJobs,
  fetchAdminConsoleVehicleAvailabilities,
  restoreAdminConsoleJob,
  updateAdminConsoleJob,
  updateAdminConsoleJobStatus,
  type AdminConsoleAuth,
  type AdminConsoleFilters,
} from "../lib/adminConsoleApi";
import type { AdminJobUpdatePayload } from "../lib/adminApi";
import type { VehicleAvailabilityItem } from "../lib/liffApi";
import {
  jobCategoryLabels,
  jobStatusLabels,
  type Job,
  type JobCategory,
  type JobStatus,
  type PostingType,
} from "../types/job";
import { formatCreatedAt, formatPrice } from "../utils/format";

const CONSOLE_STATUSES: JobStatus[] = ["open", "assigned", "closed", "completed", "cancelled", "deleted"];
const POSTING_TYPES: Array<Exclude<PostingType, null>> = ["delivery", "other"];
const JOB_CATEGORIES: Array<Exclude<JobCategory, null>> = [
  "spot",
  "charter",
  "regular",
  "work",
  "driver_recruitment",
  "referral_request",
  "other",
];

export function AdminConsolePage() {
  const [tokenInput, setTokenInput] = useState("");
  const [auth, setAuth] = useState<AdminConsoleAuth | null>(null);
  const [filters, setFilters] = useState<AdminConsoleFilters>(createEmptyAdminConsoleFilters);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [vehicles, setVehicles] = useState<VehicleAvailabilityItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );
  const editingJob = useMemo(
    () => jobs.find((job) => job.id === editingJobId) ?? null,
    [jobs, editingJobId],
  );

  const load = async (nextAuth = auth, nextFilters = filters) => {
    if (!nextAuth) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const [jobRows, vehicleRows] = await Promise.all([
        fetchAdminConsoleJobs(nextAuth, nextFilters),
        fetchAdminConsoleVehicleAvailabilities(nextAuth),
      ]);
      setJobs(jobRows);
      setVehicles(vehicleRows);
      setAuth(nextAuth);
      if (jobRows.length > 0 && !selectedJobId) {
        setSelectedJobId(jobRows[0].id);
      }
    } catch (exc) {
      setError(errorMessage(exc, "管理者データの取得に失敗しました。"));
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = tokenInput.trim();
    if (!token) {
      setError("管理者パスワードまたはトークンを入力してください。");
      return;
    }
    void load({ token });
  };

  const handleRefresh = () => {
    void load();
  };

  const handleFilterSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void load(auth, filters);
  };

  const replaceJob = (updatedJob: Job) => {
    setJobs((current) => current.map((job) => (job.id === updatedJob.id ? updatedJob : job)));
    setSelectedJobId(updatedJob.id);
  };

  const runJobAction = async (action: () => Promise<Job>, successMessage: string): Promise<boolean> => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updatedJob = await action();
      replaceJob(updatedJob);
      setMessage(successMessage);
      return true;
    } catch (exc) {
      setError(errorMessage(exc, "管理操作に失敗しました。"));
      return false;
    } finally {
      setSaving(false);
    }
  };

  const updateStatus = (job: Job, newStatus: JobStatus) => {
    if (!auth) return;
    const label = jobStatusLabels[newStatus];
    if (!window.confirm(`この案件を「${label}」に変更しますか？`)) return;
    void runJobAction(
      () => updateAdminConsoleJobStatus(auth, job.id, newStatus, `PC管理者ページで${label}へ変更`),
      `ステータスを「${label}」に変更しました。`,
    );
  };

  const deleteJob = (job: Job) => {
    if (!auth) return;
    if (!window.confirm("この投稿を削除済みにします。DB行は残ります。実行しますか？")) return;
    void runJobAction(() => deleteAdminConsoleJob(auth, job.id), "投稿を削除済みにしました。");
  };

  const restoreJob = (job: Job) => {
    if (!auth) return;
    if (!window.confirm("この削除済み案件を募集中に戻しますか？")) return;
    void runJobAction(() => restoreAdminConsoleJob(auth, job.id, "open"), "投稿を復元しました。");
  };

  const saveJob = (payload: AdminJobUpdatePayload) => {
    if (!auth || !editingJobId) return;
    void runJobAction(
      () => updateAdminConsoleJob(auth, editingJobId, payload),
      "案件を保存しました。",
    ).then((success) => {
      if (success) setEditingJobId(null);
    });
  };

  if (!auth) {
    return (
      <main className="admin-console admin-console-login">
        <section className="admin-console-login__panel">
          <h1>PC運営者管理ページ</h1>
          <p>運営者用の管理パスワードまたはトークンを入力してください。</p>
          <form onSubmit={handleLogin} className="admin-console-login__form">
            <label>
              管理者パスワード / トークン
              <input
                type="password"
                value={tokenInput}
                onChange={(event) => setTokenInput(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "確認中..." : "ログイン"}
            </button>
          </form>
          {error ? <p className="notice notice-error">{error}</p> : null}
          <p className="admin-console-login__note">
            このページはLINE内の本人用管理画面とは別の、PCブラウザ向け運営者ページです。
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-console">
      <header className="admin-console__header">
        <div>
          <h1>PC運営者管理ページ</h1>
          <p>全案件の確認、検索、編集、ステータス変更、論理削除、復元ができます。</p>
        </div>
        <div className="admin-console__header-actions">
          <a href="/?tab=companies" target="_blank" rel="noreferrer">
            企業検索を開く
          </a>
          <button type="button" onClick={handleRefresh} disabled={loading}>
            <RefreshCw aria-hidden="true" size={16} />
            更新
          </button>
          <button type="button" onClick={() => setAuth(null)}>
            ログアウト
          </button>
        </div>
      </header>

      <section className="admin-console__summary">
        <div>
          <span>全案件</span>
          <strong>{loading ? "-" : `${jobs.length}件`}</strong>
        </div>
        <div>
          <span>削除済み</span>
          <strong>{jobs.filter(isDeleted).length}件</strong>
        </div>
        <div>
          <span>空車情報</span>
          <strong>{vehicles.length}件</strong>
        </div>
      </section>

      {error ? <p className="notice notice-error">{error}</p> : null}
      {message ? <p className="notice notice-success">{message}</p> : null}

      <AdminConsoleFiltersForm
        filters={filters}
        onChange={setFilters}
        onSubmit={handleFilterSubmit}
        onReset={() => {
          const empty = createEmptyAdminConsoleFilters();
          setFilters(empty);
          void load(auth, empty);
        }}
      />

      <section className="admin-console__layout">
        <div className="admin-console__table-panel">
          <h2>全案件一覧</h2>
          <div className="admin-console-table-wrap">
            <table className="admin-console-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>status</th>
                  <th>投稿種別</th>
                  <th>案件種別</th>
                  <th>タイトル / 区間</th>
                  <th>車種</th>
                  <th>運賃</th>
                  <th>標準比</th>
                  <th>会社名</th>
                  <th>担当者</th>
                  <th>電話番号</th>
                  <th>投稿者</th>
                  <th>作成日時</th>
                  <th>更新日時</th>
                  <th>削除日時</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className={job.id === selectedJobId ? "selected" : ""}
                    onClick={() => {
                      setSelectedJobId(job.id);
                      setEditingJobId(null);
                    }}
                  >
                    <td>{shortId(job.id)}</td>
                    <td>{jobStatusLabels[job.status] ?? job.status}</td>
                    <td>{postingTypeLabel(job.posting_type)}</td>
                    <td>{job.job_category ? jobCategoryLabels[job.job_category] : "未入力"}</td>
                    <td>{jobTitle(job)}</td>
                    <td>{job.vehicle_type || "未入力"}</td>
                    <td>{formatPrice(job.price)}</td>
                    <td>{fareRatioLabel(job)}</td>
                    <td>{job.company_name || "未入力"}</td>
                    <td>{job.contact_name || "未入力"}</td>
                    <td>{job.phone_number || job.contact_phone || "未入力"}</td>
                    <td>{maskedId(job.created_by_line_user_id)}</td>
                    <td>{formatOptionalDateTime(job.created_at)}</td>
                    <td>{formatOptionalDateTime(job.updated_at)}</td>
                    <td>{formatOptionalDateTime(job.deleted_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!loading && jobs.length === 0 ? <p className="empty-state">該当する案件はありません。</p> : null}
        </div>

        <aside className="admin-console__detail-panel">
          {selectedJob ? (
            <>
              <div className="admin-console-detail__header">
                <h2>案件詳細</h2>
                <div className="admin-console-detail__actions">
                  <button type="button" onClick={() => setEditingJobId(selectedJob.id)}>
                    編集
                  </button>
                  <select
                    value={selectedJob.status}
                    onChange={(event) => updateStatus(selectedJob, event.target.value as JobStatus)}
                    disabled={saving}
                  >
                    {CONSOLE_STATUSES.map((statusValue) => (
                      <option key={statusValue} value={statusValue}>
                        {jobStatusLabels[statusValue]}
                      </option>
                    ))}
                  </select>
                  {isDeleted(selectedJob) ? (
                    <button type="button" onClick={() => restoreJob(selectedJob)} disabled={saving}>
                      復元
                    </button>
                  ) : (
                    <button type="button" className="danger-action" onClick={() => deleteJob(selectedJob)} disabled={saving}>
                      論理削除
                    </button>
                  )}
                </div>
              </div>
              {editingJob ? (
                <AdminConsoleJobEditor
                  job={editingJob}
                  saving={saving}
                  onSave={saveJob}
                  onCancel={() => setEditingJobId(null)}
                />
              ) : (
                <AdminConsoleJobDetails job={selectedJob} />
              )}
            </>
          ) : (
            <p className="empty-state">左の一覧から案件を選択してください。</p>
          )}
        </aside>
      </section>

      <section className="admin-console__vehicles">
        <h2>空車一覧</h2>
        <div className="admin-console-vehicles">
          {vehicles.map((vehicle) => (
            <article key={vehicle.id}>
              <strong>{vehicle.location || vehicle.prefecture || "場所未入力"}</strong>
              <span>車種：{vehicle.vehicle_type || "未入力"}</span>
              <span>会社名：{vehicle.company_name || "未入力"}</span>
              <span>担当者：{vehicle.contact_name || "未入力"}</span>
              <span>電話：{vehicle.contact_phone || "未入力"}</span>
              <span>状態：{vehicle.status || "未入力"}</span>
              <span>登録：{formatOptionalDateTime(vehicle.created_at)}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function AdminConsoleFiltersForm({
  filters,
  onChange,
  onSubmit,
  onReset,
}: {
  filters: AdminConsoleFilters;
  onChange: (filters: AdminConsoleFilters) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
}) {
  const setField = <K extends keyof AdminConsoleFilters>(key: K, value: AdminConsoleFilters[K]) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <form className="admin-console-filters" onSubmit={onSubmit}>
      <label>
        キーワード
        <input value={filters.q} onChange={(event) => setField("q", event.target.value)} placeholder="会社名・担当者・本文など" />
      </label>
      <label>
        status
        <select value={filters.status} onChange={(event) => setField("status", event.target.value as AdminConsoleFilters["status"])}>
          <option value="">すべて</option>
          {CONSOLE_STATUSES.map((statusValue) => (
            <option key={statusValue} value={statusValue}>
              {jobStatusLabels[statusValue]}
            </option>
          ))}
        </select>
      </label>
      <label>
        投稿種別
        <select value={filters.posting_type} onChange={(event) => setField("posting_type", event.target.value as AdminConsoleFilters["posting_type"])}>
          <option value="">すべて</option>
          {POSTING_TYPES.map((value) => (
            <option key={value} value={value}>
              {postingTypeLabel(value)}
            </option>
          ))}
        </select>
      </label>
      <label>
        案件種別
        <select value={filters.job_category} onChange={(event) => setField("job_category", event.target.value as AdminConsoleFilters["job_category"])}>
          <option value="">すべて</option>
          {JOB_CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {jobCategoryLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <label>
        車種
        <input value={filters.vehicle_type} onChange={(event) => setField("vehicle_type", event.target.value)} />
      </label>
      <label>
        会社名
        <input value={filters.company_name} onChange={(event) => setField("company_name", event.target.value)} />
      </label>
      <label>
        電話番号
        <input value={filters.phone_number} onChange={(event) => setField("phone_number", event.target.value)} />
      </label>
      <label>
        投稿日From
        <input type="date" value={filters.created_from} onChange={(event) => setField("created_from", event.target.value)} />
      </label>
      <label>
        投稿日To
        <input type="date" value={filters.created_to} onChange={(event) => setField("created_to", event.target.value)} />
      </label>
      <label className="admin-console-checkbox">
        <input type="checkbox" checked={filters.deleted_only} onChange={(event) => setField("deleted_only", event.target.checked)} />
        削除済みのみ
      </label>
      <label className="admin-console-checkbox">
        <input type="checkbox" checked={filters.open_only} onChange={(event) => setField("open_only", event.target.checked)} />
        募集中のみ
      </label>
      <label className="admin-console-checkbox">
        <input type="checkbox" checked={filters.ended_only} onChange={(event) => setField("ended_only", event.target.checked)} />
        終了案件のみ
      </label>
      <div className="admin-console-filters__actions">
        <button type="submit">
          <Search aria-hidden="true" size={16} />
          検索
        </button>
        <button type="button" onClick={onReset}>
          リセット
        </button>
      </div>
    </form>
  );
}

type EditForm = {
  posting_type: string;
  job_category: string;
  title: string;
  free_text: string;
  target_area: string;
  pickup_location: string;
  delivery_location: string;
  pickup_prefecture: string;
  pickup_city: string;
  pickup_address: string;
  delivery_prefecture: string;
  delivery_city: string;
  delivery_address: string;
  pickup_date: string;
  pickup_time_text: string;
  scheduled_date: string;
  scheduled_time_text: string;
  delivery_date: string;
  delivery_time_text: string;
  vehicle_type: string;
  vehicle_count: string;
  cargo_type: string;
  price: string;
  tax_type: string;
  fee_note: string;
  highway_fee_note: string;
  budget_note: string;
  company_name: string;
  contact_name: string;
  phone_number: string;
  notes: string;
};

function AdminConsoleJobEditor({
  job,
  saving,
  onSave,
  onCancel,
}: {
  job: Job;
  saving: boolean;
  onSave: (payload: AdminJobUpdatePayload) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<EditForm>(() => editFormFromJob(job));
  const setField = (key: keyof EditForm, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSave({
      posting_type: nullable(form.posting_type) as Job["posting_type"],
      job_category: nullable(form.job_category) as Job["job_category"],
      title: nullable(form.title),
      free_text: nullable(form.free_text),
      target_area: nullable(form.target_area),
      pickup_location: nullable(form.pickup_location),
      delivery_location: nullable(form.delivery_location),
      pickup_prefecture: nullable(form.pickup_prefecture),
      pickup_city: nullable(form.pickup_city),
      pickup_address: nullable(form.pickup_address),
      delivery_prefecture: nullable(form.delivery_prefecture),
      delivery_city: nullable(form.delivery_city),
      delivery_address: nullable(form.delivery_address),
      pickup_date: nullable(form.pickup_date),
      pickup_time_text: nullable(form.pickup_time_text),
      scheduled_date: nullable(form.scheduled_date),
      scheduled_time_text: nullable(form.scheduled_time_text),
      delivery_date: nullable(form.delivery_date),
      delivery_time_text: nullable(form.delivery_time_text),
      vehicle_type: nullable(form.vehicle_type),
      vehicle_count: numberOrNull(form.vehicle_count),
      cargo_type: nullable(form.cargo_type),
      price: numberOrNull(form.price),
      posted_fare_yen: job.posted_fare_yen ?? null,
      distance_km: job.distance_km ?? null,
      distance_text: job.distance_text ?? null,
      distance_source: job.distance_source ?? null,
      standard_fare_yen: job.standard_fare_yen ?? null,
      fare_ratio_percent: job.fare_ratio_percent ?? null,
      fare_ratio_text: job.fare_ratio_text ?? null,
      fare_judgement: job.fare_judgement ?? null,
      fare_calc_status: job.fare_calc_status ?? null,
      fare_calc_note: job.fare_calc_note ?? null,
      fare_region: job.fare_region ?? null,
      fare_vehicle_class: job.fare_vehicle_class ?? null,
      fare_vehicle_label: job.fare_vehicle_label ?? null,
      tax_type: nullable(form.tax_type) as Job["tax_type"],
      fee_note: nullable(form.fee_note),
      highway_fee_note: nullable(form.highway_fee_note),
      budget_note: nullable(form.budget_note),
      company_name: nullable(form.company_name),
      contact_name: nullable(form.contact_name),
      phone_number: nullable(form.phone_number),
      phone_numbers: nullable(form.phone_number) ? [form.phone_number.trim()] : [],
      notes: nullable(form.notes),
    });
  };

  return (
    <form className="admin-console-editor" onSubmit={handleSubmit}>
      <h3>案件編集</h3>
      <div className="admin-console-editor__grid">
        <Field label="投稿種別">
          <select value={form.posting_type} onChange={(event) => setField("posting_type", event.target.value)}>
            <option value="">未入力</option>
            {POSTING_TYPES.map((value) => (
              <option key={value} value={value}>{postingTypeLabel(value)}</option>
            ))}
          </select>
        </Field>
        <Field label="案件種別">
          <select value={form.job_category} onChange={(event) => setField("job_category", event.target.value)}>
            <option value="">未入力</option>
            {JOB_CATEGORIES.map((value) => (
              <option key={value} value={value}>{jobCategoryLabels[value]}</option>
            ))}
          </select>
        </Field>
        <TextField label="タイトル" value={form.title} onChange={(value) => setField("title", value)} />
        <TextField label="対象エリア" value={form.target_area} onChange={(value) => setField("target_area", value)} />
        <TextField label="積地全体" value={form.pickup_location} onChange={(value) => setField("pickup_location", value)} />
        <TextField label="卸地全体" value={form.delivery_location} onChange={(value) => setField("delivery_location", value)} />
        <TextField label="積地都道府県" value={form.pickup_prefecture} onChange={(value) => setField("pickup_prefecture", value)} />
        <TextField label="積地市区町村" value={form.pickup_city} onChange={(value) => setField("pickup_city", value)} />
        <TextField label="積地詳細住所" value={form.pickup_address} onChange={(value) => setField("pickup_address", value)} />
        <TextField label="卸地都道府県" value={form.delivery_prefecture} onChange={(value) => setField("delivery_prefecture", value)} />
        <TextField label="卸地市区町村" value={form.delivery_city} onChange={(value) => setField("delivery_city", value)} />
        <TextField label="卸地詳細住所" value={form.delivery_address} onChange={(value) => setField("delivery_address", value)} />
        <TextField label="集荷日" type="date" value={form.pickup_date || form.scheduled_date} onChange={(value) => {
          setField("pickup_date", value);
          setField("scheduled_date", value);
        }} />
        <TextField label="集荷時間" value={form.pickup_time_text || form.scheduled_time_text} onChange={(value) => {
          setField("pickup_time_text", value);
          setField("scheduled_time_text", value);
        }} />
        <TextField label="卸日" type="date" value={form.delivery_date} onChange={(value) => setField("delivery_date", value)} />
        <TextField label="卸時間" value={form.delivery_time_text} onChange={(value) => setField("delivery_time_text", value)} />
        <TextField label="車種" value={form.vehicle_type} onChange={(value) => setField("vehicle_type", value)} />
        <TextField label="台数" type="number" value={form.vehicle_count} onChange={(value) => setField("vehicle_count", value)} />
        <TextField label="荷物" value={form.cargo_type} onChange={(value) => setField("cargo_type", value)} />
        <TextField label="運賃" type="number" value={form.price} onChange={(value) => setField("price", value)} />
        <TextField label="税区分" value={form.tax_type} onChange={(value) => setField("tax_type", value)} />
        <TextField label="手数料メモ" value={form.fee_note} onChange={(value) => setField("fee_note", value)} />
        <TextField label="高速代メモ" value={form.highway_fee_note} onChange={(value) => setField("highway_fee_note", value)} />
        <TextField label="予算メモ" value={form.budget_note} onChange={(value) => setField("budget_note", value)} />
        <TextField label="会社名" value={form.company_name} onChange={(value) => setField("company_name", value)} />
        <TextField label="担当者" value={form.contact_name} onChange={(value) => setField("contact_name", value)} />
        <TextField label="電話番号" value={form.phone_number} onChange={(value) => setField("phone_number", value)} />
      </div>
      <label className="admin-console-editor__wide">
        案件本文
        <textarea value={form.free_text} onChange={(event) => setField("free_text", event.target.value)} rows={6} />
      </label>
      <label className="admin-console-editor__wide">
        備考
        <textarea value={form.notes} onChange={(event) => setField("notes", event.target.value)} rows={4} />
      </label>
      <div className="admin-console-editor__actions">
        <button type="submit" disabled={saving}>{saving ? "保存中..." : "保存する"}</button>
        <button type="button" onClick={onCancel}>キャンセル</button>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label>
      {label}
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function AdminConsoleJobDetails({ job }: { job: Job }) {
  return (
    <div className="admin-console-detail">
      <DetailSection title="基本情報" items={[
        ["ID", job.id],
        ["status", jobStatusLabels[job.status] ?? job.status],
        ["投稿種別", postingTypeLabel(job.posting_type)],
        ["案件種別", job.job_category ? jobCategoryLabels[job.job_category] : "未入力"],
        ["タイトル", job.title || "未入力"],
        ["本文", job.free_text || job.raw_text || "未入力"],
        ["備考", job.notes || "未入力"],
      ]} />
      <DetailSection title="通常配送情報" items={[
        ["積地", routeSide(job.pickup_location, job.pickup_prefecture, job.pickup_city, job.pickup_address)],
        ["卸地", routeSide(job.delivery_location, job.delivery_prefecture, job.delivery_city, job.delivery_address)],
        ["集荷日", job.pickup_date || job.scheduled_date || "未入力"],
        ["集荷時間", job.pickup_time_text || job.scheduled_time_text || "未入力"],
        ["卸日", job.delivery_date || "未入力"],
        ["卸時間", job.delivery_time_text || "未入力"],
        ["車種", job.vehicle_type || "未入力"],
        ["台数", job.vehicle_count != null ? `${job.vehicle_count}` : "未入力"],
        ["荷物", job.cargo_type || "未入力"],
        ["運賃", formatPrice(job.price)],
      ]} />
      <DetailSection title="連絡先" items={[
        ["会社名", job.company_name || "未入力"],
        ["担当者", job.contact_name || "未入力"],
        ["電話番号", job.phone_number || job.contact_phone || "未入力"],
        ["投稿者", maskedId(job.created_by_line_user_id)],
      ]} />
      <DetailSection title="距離・標準運賃" items={[
        ["走行距離", job.distance_text || "未計算"],
        ["車両区分", job.fare_vehicle_label || "未計算"],
        ["標準運賃目安", job.standard_fare_yen != null ? formatPrice(job.standard_fare_yen) : "未計算"],
        ["標準比", fareRatioLabel(job)],
        ["判定", job.fare_judgement || "未計算"],
        ["計算メモ", job.fare_calc_note || "未入力"],
      ]} />
      <DetailSection title="通知・削除" items={[
        ["通知先", job.notify_group_id ? "設定あり" : "未設定"],
        ["通知日時", formatOptionalDateTime(job.notified_at)],
        ["通知エラー", job.notify_error || "なし"],
        ["削除日時", formatOptionalDateTime(job.deleted_at)],
        ["削除理由", job.delete_reason || "なし"],
        ["作成日時", formatOptionalDateTime(job.created_at)],
        ["更新日時", formatOptionalDateTime(job.updated_at)],
      ]} />
    </div>
  );
}

function DetailSection({ title, items }: { title: string; items: Array<[string, string]> }) {
  return (
    <section className="admin-console-detail__section">
      <h3>{title}</h3>
      <dl>
        {items.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function editFormFromJob(job: Job): EditForm {
  return {
    posting_type: job.posting_type ?? "",
    job_category: job.job_category ?? "",
    title: job.title ?? "",
    free_text: job.free_text ?? "",
    target_area: job.target_area ?? "",
    pickup_location: job.pickup_location ?? "",
    delivery_location: job.delivery_location ?? "",
    pickup_prefecture: job.pickup_prefecture ?? "",
    pickup_city: job.pickup_city ?? "",
    pickup_address: job.pickup_address ?? "",
    delivery_prefecture: job.delivery_prefecture ?? "",
    delivery_city: job.delivery_city ?? "",
    delivery_address: job.delivery_address ?? "",
    pickup_date: job.pickup_date ?? "",
    pickup_time_text: job.pickup_time_text ?? "",
    scheduled_date: job.scheduled_date ?? "",
    scheduled_time_text: job.scheduled_time_text ?? "",
    delivery_date: job.delivery_date ?? "",
    delivery_time_text: job.delivery_time_text ?? "",
    vehicle_type: job.vehicle_type ?? "",
    vehicle_count: job.vehicle_count != null ? String(job.vehicle_count) : "",
    cargo_type: job.cargo_type ?? "",
    price: job.price != null ? String(job.price) : "",
    tax_type: job.tax_type ?? "",
    fee_note: job.fee_note ?? "",
    highway_fee_note: job.highway_fee_note ?? "",
    budget_note: job.budget_note ?? "",
    company_name: job.company_name ?? "",
    contact_name: job.contact_name ?? "",
    phone_number: job.phone_number ?? job.contact_phone ?? "",
    notes: job.notes ?? "",
  };
}

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function isDeleted(job: Job): boolean {
  return Boolean(job.deleted_at) || job.status === "deleted";
}

function shortId(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function maskedId(value?: string | null): string {
  if (!value) return "未取得";
  return `...${value.slice(-6)}`;
}

function postingTypeLabel(value?: PostingType): string {
  if (value === "delivery") return "通常配送";
  if (value === "other") return "その他";
  return "未入力";
}

function jobTitle(job: Job): string {
  if (job.title) return job.title;
  const route = routeSummary(job);
  if (route !== "区間未入力") return route;
  return job.free_text?.slice(0, 40) || job.notes?.slice(0, 40) || "タイトル未入力";
}

function routeSummary(job: Job): string {
  const pickup = [job.pickup_prefecture, job.pickup_city].filter(Boolean).join(" ") || job.pickup_location;
  const delivery = [job.delivery_prefecture, job.delivery_city].filter(Boolean).join(" ") || job.delivery_location;
  if (!pickup && !delivery) return "区間未入力";
  return `${pickup || "未入力"} → ${delivery || "未入力"}`;
}

function routeSide(
  location: string | null,
  prefecture?: string | null,
  city?: string | null,
  address?: string | null,
): string {
  const split = [prefecture, city, address].filter(Boolean).join(" ");
  return split || location || "未入力";
}

function fareRatioLabel(job: Job): string {
  if (job.fare_ratio_text) {
    return job.fare_judgement ? `${job.fare_ratio_text}（${job.fare_judgement}）` : job.fare_ratio_text;
  }
  if (job.fare_ratio_percent != null) {
    const rounded = Math.round(job.fare_ratio_percent);
    return job.fare_judgement ? `${rounded}%（${job.fare_judgement}）` : `${rounded}%`;
  }
  return "未計算";
}

function formatOptionalDateTime(value?: string | null): string {
  return value ? formatCreatedAt(value) : "未入力";
}

function errorMessage(exc: unknown, fallback: string): string {
  return exc instanceof Error ? exc.message : fallback;
}
