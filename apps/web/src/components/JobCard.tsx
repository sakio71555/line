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
  const otherPosting = isOtherPosting(job);
  const bodyPreview = jobBodyText(job);
  return (
    <article className="job-card">
      <div className="job-card__top">
        <div>
          <p className="job-card__date">{jobScheduleLabel(job)}</p>
          {otherPosting ? (
            <h2 className="job-card__route">{otherHeading(job)}</h2>
          ) : (
            <h2 className="job-card__route">
              {locationHeading(job, "pickup")}
              <span>→</span>
              {locationHeading(job, "delivery")}
            </h2>
          )}
        </div>
        <StatusBadge status={job.status} />
      </div>

      {bodyPreview ? (
        <section className="job-card__body-preview" aria-label="備考または案件本文">
          <h3>{otherPosting ? "本文" : "備考"}</h3>
          <p>{bodyPreview}</p>
        </section>
      ) : null}

      <dl className="job-card__summary">
        <SummaryField label="案件種別" value={jobCategoryLabel(job.job_category)} />
        {otherPosting ? <SummaryField label="対象エリア" value={job.target_area} /> : null}
        <SummaryField label="車種" value={job.vehicle_type} />
        <SummaryField label={otherPosting ? "内容メモ" : "荷物"} value={job.cargo_type} fallback={otherPosting ? "未入力" : "荷物未定"} />
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
            <JobField label="投稿タイプ" value={otherPosting ? "その他案件" : "通常配送案件"} />
            <JobField label="案件種別" value={jobCategoryLabel(job.job_category)} />
            <JobField label="タイトル" value={job.title} />
            <JobField label="対象エリア" value={job.target_area} />
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
            <JobField label="車両区分" value={job.fare_vehicle_label} fallback="未計算" />
            <JobField label="運輸局" value={transportRegionLabel(job.fare_region)} fallback="未判定" />
            <JobField label="標準運賃目安" value={formatOptionalYen(job.standard_fare_yen)} />
            <JobField label="投稿運賃" value={formatPrice(job.posted_fare_yen ?? job.price)} />
            <JobField label="標準比" value={fareRatioLabel(job)} />
            <JobField label="判定" value={job.fare_judgement} fallback="未計算" />
            <JobField label="計算メモ" value={job.fare_calc_note} />
            <JobField
              label="注意"
              value="標準運賃目安は、一般貨物は令和6年3月告示の標準的な運賃、軽貨物は貨物軽自動車運送事業運賃料金表をもとにした概算です。"
              wide
            />
          </JobCardSection>

          <JobCardSection title="備考">
            {otherPosting ? (
              <>
                <JobField label="本文" value={job.free_text} fallback="本文未入力" wide />
                <JobField label="備考" value={job.notes} fallback="備考なし" wide />
              </>
            ) : (
              <>
                <JobField label="備考" value={job.notes} wide />
                <JobField label="案件本文" value={job.free_text ?? job.raw_text} wide />
              </>
            )}
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

function isOtherPosting(job: Job): boolean {
  return job.posting_type === "other" || Boolean(job.title || job.free_text || job.target_area);
}

function otherHeading(job: Job): string {
  const title = displayValue(job.title, "");
  const area = displayValue(job.target_area, "");
  if (title && area) return `${title} / ${area}`;
  if (title) return title;
  if (area) return `その他案件 / ${area}`;
  return `その他案件：${jobCategoryLabel(job.job_category)}`;
}

function jobBodyText(job: Job): string | null {
  const record = job as unknown as Record<string, unknown>;
  const candidates = isOtherPosting(job)
    ? [
        job.free_text,
        job.notes,
        job.title,
        record.cargo_description,
        job.cargo_type,
        job.raw_text,
        record.description,
      ]
    : [
        job.notes,
        record.cargo_description,
        job.cargo_type,
        job.free_text,
        job.raw_text,
        record.description,
      ];
  return firstFilledText(candidates);
}

function firstFilledText(candidates: unknown[]): string | null {
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }
  return null;
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

function fareRatioLabel(job: Job): string {
  if (job.fare_ratio_text) return job.fare_ratio_text;
  return job.fare_ratio_percent != null ? `${Math.round(job.fare_ratio_percent)}%` : "未計算";
}

function fareRatioSummary(job: Job): string {
  if (job.fare_ratio_text) {
    return job.fare_judgement ? `${job.fare_ratio_text}（${job.fare_judgement}）` : job.fare_ratio_text;
  }
  if (job.fare_ratio_percent == null) return "未計算";
  const ratio = `${Math.round(job.fare_ratio_percent)}%`;
  return job.fare_judgement ? `${ratio}（${job.fare_judgement}）` : ratio;
}

function transportRegionLabel(region: string | null | undefined): string | null {
  if (!region) return null;
  return {
    kanto: "関東",
    kinki: "近畿",
    chugoku: "中国",
    shikoku: "四国",
    kyushu: "九州",
  }[region] ?? region;
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
