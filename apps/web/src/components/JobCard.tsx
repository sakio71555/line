import { useState, type ReactNode } from "react";

import { StatusBadge } from "./StatusBadge";
import { jobCategoryLabels, jobStatusLabels, type Job } from "../types/job";
import { formatCreatedAt, formatDate, formatPrice } from "../utils/format";

type Props = {
  job: Job;
  compact?: boolean;
};

export function JobCard({ job, compact = false }: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const phoneNumber = displayPhoneNumber(job);
  return (
    <article className="job-card">
      <div className="job-card__top">
        <div>
          <p className="job-card__date">{jobScheduleLabel(job)}</p>
          <h2 className="job-card__route">
            {locationHeading(job, "pickup")}
            <span>→</span>
            {locationHeading(job, "delivery")}
          </h2>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <dl className="job-card__summary">
        <SummaryField label="案件種別" value={jobCategoryLabel(job.job_category)} />
        <SummaryField label="車種" value={job.vehicle_type} />
        <SummaryField label="荷物" value={job.cargo_type} fallback="荷物未定" />
        <SummaryField label="運賃" value={formatPrice(job.price)} />
        <SummaryField label="連絡先" wide>
          <span>{displayValue(job.company_name, "会社名未入力")}</span>
          <span> / {displayValue(job.contact_name ?? job.contact_display_name, "担当者未入力")} / </span>
          {phoneNumber ? <a href={`tel:${telHref(phoneNumber)}`}>{phoneNumber}</a> : <span>電話未入力</span>}
        </SummaryField>
        <SummaryField label="距離" value={job.distance_text ?? distanceKmLabel(job.distance_km)} fallback="未計算" />
        <SummaryField label="標準比" value={fareRatioSummary(job)} />
      </dl>

      <button
        type="button"
        className="job-card__details-toggle"
        aria-expanded={detailsOpen}
        onClick={() => setDetailsOpen((current) => !current)}
      >
        {detailsOpen ? "閉じる" : "詳細を見る"}
      </button>

      {detailsOpen ? (
        <div className="job-card__details">
          <JobCardSection title="案件情報">
            <JobField label="案件種別" value={jobCategoryLabel(job.job_category)} />
            <JobField label="ステータス" value={statusLabel(job.status)} />
            <JobField label="集荷日" value={pickupDateLabel(job)} />
            <JobField label="集荷時間" value={job.pickup_time_text ?? job.scheduled_time_text} />
            <JobField label="納品日" value={dateLabel(job.delivery_date)} />
            <JobField label="納品時間" value={job.delivery_time_text} />
            <JobField label="車種" value={job.vehicle_type} />
            <JobField label="台数" value={job.vehicle_count != null ? `${job.vehicle_count}台` : null} />
            <JobField label="荷物" value={job.cargo_type} fallback="荷物未定" />
            <JobField label="運賃" value={formatPrice(job.price)} />
            <JobField label="税区分" value={job.tax_type} />
            <JobField label="高速代" value={job.highway_fee_note} />
            <JobField label="手数料メモ" value={job.fee_note} />
            {compact ? <JobField label="取込元" value={sourceLabel(job.source_type)} /> : null}
          </JobCardSection>

          <JobCardSection title="積地">
            <JobField label="都道府県" value={job.pickup_prefecture} />
            <JobField label="市区町村" value={job.pickup_city} />
            <JobField label="詳細住所" value={job.pickup_address} />
            <JobField label="住所全体" value={job.pickup_location} />
          </JobCardSection>

          <JobCardSection title="卸地">
            <JobField label="都道府県" value={job.delivery_prefecture} />
            <JobField label="市区町村" value={job.delivery_city} />
            <JobField label="詳細住所" value={job.delivery_address} />
            <JobField label="住所全体" value={job.delivery_location} />
          </JobCardSection>

          <JobCardSection title="連絡先">
            {compact ? <JobField label="投稿者" value={job.created_by_display_name} fallback="未取得" /> : null}
            <JobField label="会社名" value={job.company_name} />
            <JobField label="担当者" value={job.contact_name ?? job.contact_display_name} />
            <JobField label="電話" value={phoneNumber} href={phoneNumber ? `tel:${telHref(phoneNumber)}` : null} />
            {compact ? <JobField label="連絡方法" value={contactMethodLabel(job.contact_method)} /> : null}
          </JobCardSection>

          <JobCardSection title="距離・標準運賃">
            <JobField label="走行距離" value={job.distance_text ?? distanceKmLabel(job.distance_km)} fallback="未計算" />
            <JobField label="算出区分" value={job.fare_vehicle_label} fallback="未計算" />
            <JobField label="標準運賃目安" value={formatOptionalYen(job.standard_fare_yen)} />
            <JobField label="投稿運賃" value={formatPrice(job.price)} />
            <JobField label="標準比" value={fareRatioLabel(job.fare_ratio_percent)} />
            <JobField label="判定" value={job.fare_judgement} fallback="未計算" />
            <JobField label="計算メモ" value={job.fare_calc_note} />
          </JobCardSection>

          <JobCardSection title="備考">
            <JobField label="備考" value={job.notes} wide />
            <JobField label="予算メモ" value={job.budget_note} wide />
          </JobCardSection>
        </div>
      ) : null}

      <div className="job-card__bottom">
        <strong>{formatPrice(job.price)}</strong>
        <div className="job-card__badges">
          {job.contact_missing ? (
            <span className="badge badge-contact-missing">連絡先確認が必要</span>
          ) : null}
          {job.review_required ? (
            <span className="badge badge-review">確認待ち</span>
          ) : null}
          <StatusBadge status={job.analysis_status} tone="analysis" />
        </div>
      </div>

      <p className="job-card__created">登録：{formatCreatedAt(job.created_at) || "未入力"}</p>
    </article>
  );
}

function SummaryField({
  label,
  value,
  fallback = "未入力",
  wide = false,
  children,
}: {
  label: string;
  value?: string | number | null;
  fallback?: string;
  wide?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className={wide ? "job-card__summary-field job-card__summary-field--wide" : "job-card__summary-field"}>
      <dt>{label}</dt>
      <dd>{children ?? displayValue(value, fallback)}</dd>
    </div>
  );
}

function JobCardSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="job-card__section" aria-label={title}>
      <h3>{title}</h3>
      <dl>{children}</dl>
    </section>
  );
}

function JobField({
  label,
  value,
  fallback = "未入力",
  href,
  wide = false,
}: {
  label: string;
  value: string | number | null | undefined;
  fallback?: string;
  href?: string | null;
  wide?: boolean;
}) {
  const display = displayValue(value, fallback);
  return (
    <div className={wide ? "job-card__field job-card__field--wide" : "job-card__field"}>
      <dt>{label}</dt>
      <dd>{href && display !== fallback ? <a href={href}>{display}</a> : display}</dd>
    </div>
  );
}

function sourceLabel(sourceType: Job["source_type"]): string {
  if (sourceType === "liff_form") return "フォーム投稿";
  if (sourceType === "line_group") return "LINEグループ";
  if (sourceType === "admin_manual") return "管理者作成";
  if (sourceType === "line_history_import") return "過去ログ取込";
  return "取込元未定";
}

function contactMethodLabel(method: Job["contact_method"]): string {
  if (method === "phone") return "本文電話";
  if (method === "registered_phone") return "登録電話";
  if (method === "form") return "フォーム";
  if (method === "group_reply_or_admin") return "グループ返信/管理者確認";
  return "未設定";
}

function jobCategoryLabel(category: Job["job_category"]): string {
  return category ? (jobCategoryLabels[category] ?? category) : "未入力";
}

function statusLabel(status: Job["status"]): string {
  return jobStatusLabels[status] ?? status ?? "未入力";
}

function displayPhoneNumber(job: Job): string | null {
  return job.phone_number ?? job.contact_phone ?? job.phone_numbers?.find((phone) => phone.trim()) ?? null;
}

function telHref(phoneNumber: string): string {
  return phoneNumber.replace(/[^\d+]/g, "");
}

function jobScheduleLabel(job: Job): string {
  if (job.recurring && job.schedule_text) return job.schedule_text;
  const dateValue = job.pickup_date ?? job.scheduled_date;
  if (!dateValue) return job.schedule_text ?? "日付未確定";
  const parts = [formatDate(dateValue)];
  const timeText = job.pickup_time_text ?? job.scheduled_time_text;
  if (timeText) parts.push(timeText);
  parts.push("集荷");
  return parts.join(" ");
}

function locationHeading(job: Job, type: "pickup" | "delivery"): string {
  const prefecture = type === "pickup" ? job.pickup_prefecture : job.delivery_prefecture;
  const city = type === "pickup" ? job.pickup_city : job.delivery_city;
  const location = type === "pickup" ? job.pickup_location : job.delivery_location;
  const summary = [prefecture, city].filter(isFilled).join(" ");
  return summary || location || (type === "pickup" ? "積地未入力" : "卸地未入力");
}

function pickupDateLabel(job: Job): string {
  if (job.pickup_date) return formatDate(job.pickup_date);
  if (job.scheduled_date) return formatDate(job.scheduled_date);
  return job.schedule_text ?? "日付未確定";
}

function dateLabel(value: string | null): string {
  return value ? formatDate(value) : "未入力";
}

function distanceKmLabel(value: number | null | undefined): string | null {
  return value != null ? `約${Math.round(value)}km` : null;
}

function fareRatioLabel(value: number | null | undefined): string {
  return value != null ? `${Math.round(value)}%` : "未計算";
}

function fareRatioSummary(job: Job): string {
  if (job.fare_ratio_percent == null) return "未計算";
  const ratio = `${Math.round(job.fare_ratio_percent)}%`;
  return job.fare_judgement ? `${ratio}（${job.fare_judgement}）` : ratio;
}

function formatOptionalYen(value: number | null | undefined): string {
  return value != null ? formatPrice(value) : "未計算";
}

function displayValue(value: string | number | null | undefined, fallback: string): string {
  if (typeof value === "number") return String(value);
  if (typeof value === "string" && value.trim()) return value.trim();
  return fallback;
}

function isFilled(value: string | null | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}
