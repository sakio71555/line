import { RefreshCw } from "lucide-react";

import { useVehicleAvailabilities } from "../hooks/useVehicleAvailabilities";
import type { VehicleAvailabilityItem } from "../lib/liffApi";
import { formatCreatedAt, formatDate } from "../utils/format";

export function VehicleAvailabilityListPage() {
  const { vehicleAvailabilities, loading, error, reload } = useVehicleAvailabilities();

  return (
    <>
      <section className="list-summary">
        <strong>{loading ? "読み込み中" : `${vehicleAvailabilities.length}件`}</strong>
        <span>登録済みの空車情報を表示しています</span>
        <button type="button" className="icon-button" onClick={reload} aria-label="空車一覧を更新">
          <RefreshCw aria-hidden="true" size={16} />
        </button>
      </section>

      {error ? <p className="notice notice-error">{error}</p> : null}

      <div className="vehicle-list">
        {vehicleAvailabilities.map((vehicle) => (
          <VehicleAvailabilityCard key={vehicle.id} vehicle={vehicle} />
        ))}
      </div>

      {!loading && vehicleAvailabilities.length === 0 ? (
        <p className="empty-state">登録されている空車情報はありません</p>
      ) : null}
    </>
  );
}

function VehicleAvailabilityCard({ vehicle }: { vehicle: VehicleAvailabilityItem }) {
  const phoneNumber = displayPhoneNumber(vehicle);
  return (
    <article className="vehicle-card">
      <div className="vehicle-card__top">
        <div>
          <p className="vehicle-card__date">{availableDateLabel(vehicle)}</p>
          <h2>{vehicle.location || vehicle.prefecture || "空車場所未入力"}</h2>
        </div>
        <span className="badge badge-open">{vehicle.status === "open" ? "空車" : vehicle.status || "状態未入力"}</span>
      </div>

      <div className="vehicle-card__meta">
        <span>車種：{vehicle.vehicle_type || "未入力"}</span>
        <span>地域：{vehicle.prefecture || "未入力"}</span>
        <span>登録：{formatCreatedAt(vehicle.created_at)}</span>
      </div>

      <section className="vehicle-card__contact" aria-label="空車連絡先">
        <h3>連絡先</h3>
        <span>会社名：{vehicle.company_name || "未入力"}</span>
        <span>担当者：{vehicle.contact_name || "未入力"}</span>
        <span>
          電話：
          {phoneNumber ? <a href={`tel:${telHref(phoneNumber)}`}>{phoneNumber}</a> : "未入力"}
        </span>
      </section>

      <dl className="vehicle-card__details">
        <div>
          <dt>備考</dt>
          <dd>{vehicle.notes || fallbackRawText(vehicle.raw_text) || "未入力"}</dd>
        </div>
      </dl>
    </article>
  );
}

function availableDateLabel(vehicle: VehicleAvailabilityItem): string {
  if (vehicle.available_date) return `${formatDate(vehicle.available_date)} 空車`;
  if (vehicle.available_from) return `${formatCreatedAt(vehicle.available_from)} から`;
  return "日付未入力";
}

function displayPhoneNumber(vehicle: VehicleAvailabilityItem): string | null {
  return vehicle.contact_phone ?? vehicle.phone_numbers?.find((phone) => phone.trim()) ?? null;
}

function telHref(phoneNumber: string): string {
  return phoneNumber.replace(/[^\d+]/g, "");
}

function fallbackRawText(rawText: string | null): string | null {
  if (!rawText) return null;
  const trimmed = rawText.trim();
  return trimmed.length > 160 ? `${trimmed.slice(0, 160)}...` : trimmed;
}

