import { RotateCw, Save, X } from "lucide-react";
import { useEffect, useState } from "react";

import type { AdminJobUpdatePayload } from "../lib/adminApi";
import { measureDistance, type DistanceMeasureResult } from "../lib/liffApi";
import { jobCategoryLabels, type Job, type JobCategory } from "../types/job";
import { formatPrice } from "../utils/format";
import { isVehicleTypeOption, vehicleTypeOptions } from "../constants/vehicleTypes";

type Props = {
  job: Job;
  saving: boolean;
  onSave: (payload: AdminJobUpdatePayload) => void;
  onClose: () => void;
};

const jobCategories: Exclude<JobCategory, null>[] = [
  "spot",
  "charter",
  "regular",
  "work",
  "driver_recruitment",
  "referral_request",
  "other",
];

function toFormValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

export function AdminJobEditor({ job, saving, onSave, onClose }: Props) {
  const [distanceResult, setDistanceResult] = useState<DistanceMeasureResult | null>(null);
  const [distanceError, setDistanceError] = useState<string | null>(null);
  const [distanceLoading, setDistanceLoading] = useState(false);
  const [distanceDirty, setDistanceDirty] = useState(false);
  const [form, setForm] = useState({
    job_category: "spot" as Exclude<JobCategory, null>,
    posting_type: "delivery" as NonNullable<Job["posting_type"]>,
    title: "",
    free_text: "",
    target_area: "",
    pickup_location: "",
    delivery_location: "",
    pickup_prefecture: "",
    pickup_city: "",
    pickup_address: "",
    delivery_prefecture: "",
    delivery_city: "",
    delivery_address: "",
    pickup_date: "",
    pickup_time_text: "",
    scheduled_date: "",
    scheduled_time_text: "",
    delivery_date: "",
    delivery_time_text: "",
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
    phone_number: "",
    notes: "",
  });

  useEffect(() => {
    setDistanceResult(null);
    setDistanceError(null);
    setDistanceDirty(false);
    setForm({
      job_category: job.job_category ?? "spot",
      posting_type: job.posting_type ?? "delivery",
      title: toFormValue(job.title),
      free_text: toFormValue(job.free_text),
      target_area: toFormValue(job.target_area),
      pickup_location: toFormValue(job.pickup_location),
      delivery_location: toFormValue(job.delivery_location),
      pickup_prefecture: toFormValue(job.pickup_prefecture),
      pickup_city: toFormValue(job.pickup_city),
      pickup_address: toFormValue(job.pickup_address),
      delivery_prefecture: toFormValue(job.delivery_prefecture),
      delivery_city: toFormValue(job.delivery_city),
      delivery_address: toFormValue(job.delivery_address),
      pickup_date: toFormValue(job.pickup_date ?? job.scheduled_date),
      pickup_time_text: toFormValue(job.pickup_time_text ?? job.scheduled_time_text),
      scheduled_date: toFormValue(job.scheduled_date),
      scheduled_time_text: toFormValue(job.scheduled_time_text),
      delivery_date: toFormValue(job.delivery_date),
      delivery_time_text: toFormValue(job.delivery_time_text),
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
      phone_number: toFormValue(job.phone_number ?? job.contact_phone ?? job.phone_numbers?.[0]),
      notes: toFormValue(job.notes),
    });
  }, [job]);

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (["pickup_prefecture", "pickup_city", "pickup_address", "delivery_prefecture", "delivery_city", "delivery_address", "vehicle_type", "price"].includes(field)) {
      setDistanceDirty(true);
      setDistanceResult(null);
      setDistanceError("車種・住所・運賃を変更したため、保存前に距離・標準運賃を再計算してください。");
    }
  };

  const submit = () => {
    const isOtherPosting = form.posting_type === "other";
    const pickupLocation = buildLocation(form.pickup_prefecture, form.pickup_city, form.pickup_address);
    const deliveryLocation = buildLocation(form.delivery_prefecture, form.delivery_city, form.delivery_address);
    const distanceFields = distanceResult
      ? {
          distance_km: distanceResult.distance_km,
          distance_text: distanceResult.distance_text,
          distance_source: distanceResult.distance_source,
          posted_fare_yen: distanceResult.posted_fare_yen ?? (form.price ? Number(form.price) : null),
          standard_fare_yen: distanceResult.standard_fare_yen,
          fare_ratio_percent: distanceResult.fare_ratio_percent,
          fare_ratio_text: distanceResult.fare_ratio_text,
          fare_judgement: distanceResult.fare_judgement,
          fare_calc_status: distanceResult.fare_calc_status,
          fare_calc_note: distanceResult.fare_calc_note,
          fare_region: distanceResult.fare_region ?? null,
          fare_vehicle_class: distanceResult.fare_vehicle_class,
          fare_vehicle_label: distanceResult.fare_vehicle_label,
        }
      : isOtherPosting
        ? {
            distance_km: null,
            distance_text: null,
            distance_source: null,
            posted_fare_yen: form.price ? Number(form.price) : null,
            standard_fare_yen: null,
            fare_ratio_percent: null,
            fare_ratio_text: null,
            fare_judgement: null,
            fare_calc_status: "not_applicable",
            fare_calc_note: "積地・卸地を指定しない案件のため",
            fare_region: null,
            fare_vehicle_class: null,
            fare_vehicle_label: null,
          }
        : distanceDirty
        ? {
            distance_km: null,
            distance_text: null,
            distance_source: null,
            posted_fare_yen: form.price ? Number(form.price) : null,
            standard_fare_yen: null,
            fare_ratio_percent: null,
            fare_ratio_text: null,
            fare_judgement: null,
            fare_calc_status: "not_calculated",
            fare_calc_note: "車種・住所・運賃が変更されたため再計算が必要です",
            fare_region: null,
            fare_vehicle_class: null,
            fare_vehicle_label: null,
          }
        : {};
    onSave({
      posting_type: form.posting_type,
      job_category: form.job_category,
      title: form.title || null,
      free_text: form.free_text || null,
      target_area: form.target_area || null,
      pickup_location: pickupLocation || form.pickup_location || null,
      delivery_location: deliveryLocation || form.delivery_location || null,
      pickup_prefecture: form.pickup_prefecture || null,
      pickup_city: form.pickup_city || null,
      pickup_address: form.pickup_address || null,
      delivery_prefecture: form.delivery_prefecture || null,
      delivery_city: form.delivery_city || null,
      delivery_address: form.delivery_address || null,
      pickup_date: form.pickup_date || null,
      pickup_time_text: form.pickup_time_text || null,
      scheduled_date: form.pickup_date || form.scheduled_date || null,
      scheduled_time_text: form.pickup_time_text || form.scheduled_time_text || null,
      delivery_date: form.delivery_date || null,
      delivery_time_text: form.delivery_time_text || null,
      vehicle_type: form.vehicle_type || null,
      vehicle_count: form.vehicle_count ? Number(form.vehicle_count) : null,
      cargo_type: form.cargo_type || null,
      price: form.price ? Number(form.price) : null,
      ...distanceFields,
      tax_type: form.tax_type ? (form.tax_type as "税別" | "税込" | "不明") : null,
      fee_note: form.fee_note || null,
      highway_fee_note: form.highway_fee_note || null,
      budget_note: form.budget_note || null,
      company_name: form.company_name || null,
      contact_name: form.contact_name || null,
      phone_number: form.phone_number || null,
      phone_numbers: form.phone_number ? [form.phone_number] : [],
      notes: form.notes || null,
    });
  };

  const recalculateDistance = async () => {
    if (
      !form.pickup_prefecture.trim() ||
      !form.pickup_city.trim() ||
      !form.delivery_prefecture.trim() ||
      !form.delivery_city.trim()
    ) {
      setDistanceError("積地・卸地の都道府県と市区町村を入力してください");
      return;
    }
    const pickupAddress = buildAddress(form.pickup_prefecture, form.pickup_city, form.pickup_address);
    const deliveryAddress = buildAddress(form.delivery_prefecture, form.delivery_city, form.delivery_address);

    setDistanceLoading(true);
    setDistanceError(null);
    try {
      const result = await measureDistance({
        pickup_address: pickupAddress,
        delivery_address: deliveryAddress,
        pickup_prefecture: form.pickup_prefecture,
        vehicle_type: form.vehicle_type,
        posted_fare: form.price || null,
        pickup_detail_missing: !form.pickup_address.trim(),
        delivery_detail_missing: !form.delivery_address.trim(),
      });
      setDistanceResult(result);
      setDistanceDirty(false);
      if (result.fare_calc_status !== "ok") {
        setDistanceError(result.fare_calc_note ?? "距離・標準運賃を計算できませんでした");
      }
    } catch (exc) {
      setDistanceError(errorMessage(exc, "距離・標準運賃を再計算できませんでした"));
    } finally {
      setDistanceLoading(false);
    }
  };

  const pickupLocationPreview = buildLocation(form.pickup_prefecture, form.pickup_city, form.pickup_address) || form.pickup_location;
  const deliveryLocationPreview =
    buildLocation(form.delivery_prefecture, form.delivery_city, form.delivery_address) || form.delivery_location;

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

      <p className="notice">
        住所・車種・運賃を変更した場合は、保存前に「距離・運賃を再計算」を押してください。標準運賃目安は、一般貨物は令和6年3月告示の標準的な運賃、軽貨物は貨物軽自動車運送事業運賃料金表をもとにした概算です。
      </p>

      <div className="admin-editor__grid">
        <label>
          <span>投稿タイプ</span>
          <select value={form.posting_type} onChange={(event) => update("posting_type", event.target.value)}>
            <option value="delivery">通常配送案件</option>
            <option value="other">その他案件</option>
          </select>
        </label>
        <label>
          <span>案件種別</span>
          <select value={form.job_category} onChange={(event) => update("job_category", event.target.value)}>
            {jobCategories.map((category) => (
              <option key={category} value={category}>
                {jobCategoryLabels[category]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>タイトル</span>
          <input value={form.title} onChange={(event) => update("title", event.target.value)} />
        </label>
        <label>
          <span>対象エリア</span>
          <input value={form.target_area} onChange={(event) => update("target_area", event.target.value)} />
        </label>
        <label className="admin-editor__wide">
          <span>案件本文</span>
          <textarea value={form.free_text} onChange={(event) => update("free_text", event.target.value)} rows={5} />
        </label>
        <label>
          <span>積地全体（自動）</span>
          <input
            value={pickupLocationPreview}
            readOnly
            aria-readonly="true"
          />
        </label>
        <label>
          <span>積地都道府県</span>
          <input
            value={form.pickup_prefecture}
            onChange={(event) => update("pickup_prefecture", event.target.value)}
          />
        </label>
        <label>
          <span>積地市区町村</span>
          <input
            value={form.pickup_city}
            onChange={(event) => update("pickup_city", event.target.value)}
          />
        </label>
        <label>
          <span>積地詳細住所</span>
          <input
            value={form.pickup_address}
            onChange={(event) => update("pickup_address", event.target.value)}
          />
        </label>
        <label>
          <span>卸地全体（自動）</span>
          <input
            value={deliveryLocationPreview}
            readOnly
            aria-readonly="true"
          />
        </label>
        <label>
          <span>卸地都道府県</span>
          <input
            value={form.delivery_prefecture}
            onChange={(event) => update("delivery_prefecture", event.target.value)}
          />
        </label>
        <label>
          <span>卸地市区町村</span>
          <input
            value={form.delivery_city}
            onChange={(event) => update("delivery_city", event.target.value)}
          />
        </label>
        <label>
          <span>卸地詳細住所</span>
          <input
            value={form.delivery_address}
            onChange={(event) => update("delivery_address", event.target.value)}
          />
        </label>
        <label>
          <span>集荷日</span>
          <input
            type="date"
            value={form.pickup_date}
            onChange={(event) => update("pickup_date", event.target.value)}
          />
        </label>
        <label>
          <span>集荷時間</span>
          <input
            value={form.pickup_time_text}
            onChange={(event) => update("pickup_time_text", event.target.value)}
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
          <span>卸時間</span>
          <input
            value={form.delivery_time_text}
            onChange={(event) => update("delivery_time_text", event.target.value)}
          />
        </label>
        <label>
          <span>車種</span>
          <select value={form.vehicle_type} onChange={(event) => update("vehicle_type", event.target.value)}>
            {form.vehicle_type && !isVehicleTypeOption(form.vehicle_type) ? (
              <option value={form.vehicle_type}>{form.vehicle_type}（既存値）</option>
            ) : null}
            {vehicleTypeOptions.map((vehicleType) => (
              <option value={vehicleType} key={vehicleType}>
                {vehicleType}
              </option>
            ))}
          </select>
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
            value={form.phone_number}
            onChange={(event) => update("phone_number", event.target.value)}
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

      {form.posting_type === "delivery" ? (
      <section className="admin-editor__distance">
        <div>
          <h3>距離・標準運賃</h3>
          <p>
            走行距離・標準運賃目安は概算です。詳細住所が未入力の場合、距離が実際と異なる場合があります。
          </p>
          <p>{distancePreview(distanceResult, job)}</p>
          {distanceError ? <p className="notice notice-warning">{distanceError}</p> : null}
        </div>
        <button type="button" onClick={recalculateDistance} disabled={saving || distanceLoading}>
          <RotateCw aria-hidden="true" size={16} />
          {distanceLoading ? "距離を取得中..." : "距離・運賃を再計算"}
        </button>
      </section>
      ) : (
        <p className="notice">その他案件は積地・卸地を指定しない前提のため、距離・標準運賃は対象外として保存します。</p>
      )}

      <div className="admin-editor__actions">
        <button type="button" className="primary-action" onClick={submit} disabled={saving}>
          <Save aria-hidden="true" size={16} />
          保存する
        </button>
        <button type="button" onClick={onClose} disabled={saving}>
          <X aria-hidden="true" size={16} />
          キャンセル
        </button>
      </div>
    </section>
  );
}

function buildLocation(prefecture: string, city: string, address: string): string {
  return [prefecture, city, address]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
}

function buildAddress(prefecture: string, city: string, address: string): string {
  return [prefecture, city, address]
    .map((value) => value.trim())
    .filter((value) => value && value !== "未入力")
    .join("");
}

function distancePreview(result: DistanceMeasureResult | null, job: Job): string {
  const distanceText = result?.distance_text ?? job.distance_text ?? (job.distance_km != null ? `約${Math.round(job.distance_km)}km` : "未計算");
  const standardFare = result?.standard_fare_yen ?? job.standard_fare_yen;
  const ratio = result?.fare_ratio_percent ?? job.fare_ratio_percent;
  const judgement = result?.fare_judgement ?? job.fare_judgement;
  const vehicleLabel = result?.fare_vehicle_label ?? job.fare_vehicle_label ?? "未計算";
  const region = transportRegionLabel(result?.fare_region ?? job.fare_region);
  const ratioText = ratio != null ? `${Math.round(ratio)}%${judgement ? `（${judgement}）` : ""}` : "未計算";
  return `走行距離：${distanceText} / 車両区分：${vehicleLabel} / 運輸局：${region} / 標準運賃目安：${standardFare != null ? formatPrice(standardFare) : "未計算"} / 標準比：${ratioText}`;
}

function transportRegionLabel(region: string | null | undefined): string {
  if (!region) return "未判定";
  return {
    kanto: "関東",
    kinki: "近畿",
    chugoku: "中国",
    shikoku: "四国",
    kyushu: "九州",
  }[region] ?? region;
}

function errorMessage(exc: unknown, fallback: string): string {
  if (exc instanceof Error && exc.message) {
    return exc.message;
  }
  return fallback;
}
