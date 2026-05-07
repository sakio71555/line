import { EyeOff, Save, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";

import type { AdminJobUpdatePayload } from "../lib/adminApi";
import { jobStatusLabels, type Job, type JobStatus } from "../types/job";

type Props = {
  job: Job;
  saving: boolean;
  onSave: (payload: AdminJobUpdatePayload) => void;
  onVerify: () => void;
  onHide: () => void;
  onClose: () => void;
};

const statuses: JobStatus[] = [
  "needs_review",
  "open",
  "negotiating",
  "assigned",
  "in_progress",
  "completed",
  "cancelled",
  "hidden",
];

function toFormValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

export function AdminJobEditor({ job, saving, onSave, onVerify, onHide, onClose }: Props) {
  const [form, setForm] = useState({
    pickup_location: "",
    delivery_location: "",
    pickup_prefecture: "",
    delivery_prefecture: "",
    scheduled_date: "",
    scheduled_time_text: "",
    delivery_date: "",
    vehicle_type: "",
    vehicle_count: "",
    cargo_type: "",
    price: "",
    tax_type: "",
    fee_note: "",
    highway_fee_note: "",
    budget_note: "",
    company_name: "",
    contact_name: "",
    phone_numbers: "",
    notes: "",
    status: "needs_review" as JobStatus,
  });

  useEffect(() => {
    setForm({
      pickup_location: toFormValue(job.pickup_location),
      delivery_location: toFormValue(job.delivery_location),
      pickup_prefecture: toFormValue(job.pickup_prefecture),
      delivery_prefecture: toFormValue(job.delivery_prefecture),
      scheduled_date: toFormValue(job.scheduled_date),
      scheduled_time_text: toFormValue(job.scheduled_time_text),
      delivery_date: toFormValue(job.delivery_date),
      vehicle_type: toFormValue(job.vehicle_type),
      vehicle_count: toFormValue(job.vehicle_count),
      cargo_type: toFormValue(job.cargo_type),
      price: toFormValue(job.price),
      tax_type: toFormValue(job.tax_type),
      fee_note: toFormValue(job.fee_note),
      highway_fee_note: toFormValue(job.highway_fee_note),
      budget_note: toFormValue(job.budget_note),
      company_name: toFormValue(job.company_name),
      contact_name: toFormValue(job.contact_name),
      phone_numbers: toFormValue(job.phone_numbers?.join(", ")),
      notes: toFormValue(job.notes),
      status: job.status,
    });
  }, [job]);

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = () => {
    onSave({
      pickup_location: form.pickup_location || null,
      delivery_location: form.delivery_location || null,
      pickup_prefecture: form.pickup_prefecture || null,
      delivery_prefecture: form.delivery_prefecture || null,
      scheduled_date: form.scheduled_date || null,
      scheduled_time_text: form.scheduled_time_text || null,
      delivery_date: form.delivery_date || null,
      vehicle_type: form.vehicle_type || null,
      vehicle_count: form.vehicle_count ? Number(form.vehicle_count) : null,
      cargo_type: form.cargo_type || null,
      price: form.price ? Number(form.price) : null,
      tax_type: form.tax_type ? (form.tax_type as "税別" | "税込" | "不明") : null,
      fee_note: form.fee_note || null,
      highway_fee_note: form.highway_fee_note || null,
      budget_note: form.budget_note || null,
      company_name: form.company_name || null,
      contact_name: form.contact_name || null,
      phone_numbers: form.phone_numbers
        ? form.phone_numbers
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean)
        : null,
      notes: form.notes || null,
      status: form.status,
    });
  };

  return (
    <section className="admin-editor" aria-label="案件編集フォーム">
      <div className="admin-editor__header">
        <div>
          <p>編集中</p>
          <h2>
            {job.pickup_location ?? "出発地未定"} → {job.delivery_location ?? "到着地未定"}
          </h2>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="閉じる">
          <X aria-hidden="true" size={18} />
        </button>
      </div>

      <div className="admin-editor__grid">
        <label>
          <span>出発地</span>
          <input
            value={form.pickup_location}
            onChange={(event) => update("pickup_location", event.target.value)}
          />
        </label>
        <label>
          <span>到着地</span>
          <input
            value={form.delivery_location}
            onChange={(event) => update("delivery_location", event.target.value)}
          />
        </label>
        <label>
          <span>出発県</span>
          <input
            value={form.pickup_prefecture}
            onChange={(event) => update("pickup_prefecture", event.target.value)}
          />
        </label>
        <label>
          <span>到着県</span>
          <input
            value={form.delivery_prefecture}
            onChange={(event) => update("delivery_prefecture", event.target.value)}
          />
        </label>
        <label>
          <span>集荷日</span>
          <input
            type="date"
            value={form.scheduled_date}
            onChange={(event) => update("scheduled_date", event.target.value)}
          />
        </label>
        <label>
          <span>集荷時間</span>
          <input
            value={form.scheduled_time_text}
            onChange={(event) => update("scheduled_time_text", event.target.value)}
          />
        </label>
        <label>
          <span>納品日</span>
          <input
            type="date"
            value={form.delivery_date}
            onChange={(event) => update("delivery_date", event.target.value)}
          />
        </label>
        <label>
          <span>車種</span>
          <input
            value={form.vehicle_type}
            onChange={(event) => update("vehicle_type", event.target.value)}
          />
        </label>
        <label>
          <span>台数</span>
          <input
            inputMode="numeric"
            min="1"
            type="number"
            value={form.vehicle_count}
            onChange={(event) => update("vehicle_count", event.target.value)}
          />
        </label>
        <label>
          <span>荷物</span>
          <input
            value={form.cargo_type}
            onChange={(event) => update("cargo_type", event.target.value)}
          />
        </label>
        <label>
          <span>運賃</span>
          <input
            inputMode="numeric"
            min="0"
            type="number"
            value={form.price}
            onChange={(event) => update("price", event.target.value)}
          />
        </label>
        <label>
          <span>税区分</span>
          <select value={form.tax_type} onChange={(event) => update("tax_type", event.target.value)}>
            <option value="">未設定</option>
            <option value="税別">税別</option>
            <option value="税込">税込</option>
            <option value="不明">不明</option>
          </select>
        </label>
        <label>
          <span>ステータス</span>
          <select
            value={form.status}
            onChange={(event) => update("status", event.target.value)}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {jobStatusLabels[status]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>高速代</span>
          <input
            value={form.highway_fee_note}
            onChange={(event) => update("highway_fee_note", event.target.value)}
          />
        </label>
        <label>
          <span>手数料メモ</span>
          <input
            value={form.fee_note}
            onChange={(event) => update("fee_note", event.target.value)}
          />
        </label>
        <label>
          <span>予算メモ</span>
          <input
            value={form.budget_note}
            onChange={(event) => update("budget_note", event.target.value)}
          />
        </label>
        <label>
          <span>会社名</span>
          <input
            value={form.company_name}
            onChange={(event) => update("company_name", event.target.value)}
          />
        </label>
        <label>
          <span>担当者名</span>
          <input
            value={form.contact_name}
            onChange={(event) => update("contact_name", event.target.value)}
          />
        </label>
        <label>
          <span>電話番号</span>
          <input
            value={form.phone_numbers}
            onChange={(event) => update("phone_numbers", event.target.value)}
          />
        </label>
        <label className="admin-editor__wide">
          <span>備考</span>
          <textarea
            value={form.notes}
            onChange={(event) => update("notes", event.target.value)}
            rows={3}
          />
        </label>
      </div>

      <div className="admin-editor__actions">
        <button type="button" className="primary-action" onClick={submit} disabled={saving}>
          <Save aria-hidden="true" size={16} />
          保存
        </button>
        <button type="button" onClick={onVerify} disabled={saving}>
          <ShieldCheck aria-hidden="true" size={16} />
          確認完了
        </button>
        <button type="button" className="danger-action" onClick={onHide} disabled={saving}>
          <EyeOff aria-hidden="true" size={16} />
          非公開
        </button>
      </div>
    </section>
  );
}
