import { ListChecks, RotateCcw, Send, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent } from "react";

import { measureDistance, submitLiffJob, type DistanceMeasureResult, type LiffJobPayload } from "../lib/liffApi";
import { closeLiffWindow, type LiffProfileState } from "../lib/liff";
import { webEnv } from "../lib/env";
import { formatPrice } from "../utils/format";
import { vehicleTypeOptions } from "../constants/vehicleTypes";

type Props = {
  profile: LiffProfileState;
  sessionId: string | null;
  onNavigateToJobs: () => void;
};

const initialForm = {
  posting_type: "delivery",
  job_category: "spot",
  title: "",
  free_text: "",
  target_area: "",
  pickup_prefecture: "",
  pickup_city: "",
  pickup_address: "",
  delivery_prefecture: "",
  delivery_city: "",
  delivery_address: "",
  scheduled_date: "",
  scheduled_time_text: "",
  delivery_date: "",
  delivery_time_text: "",
  vehicle_type: "軽バン",
  vehicle_count: "1",
  cargo_type: "",
  price: "",
  tax_type: "不明",
  highway_fee_note: "",
  fee_note: "",
  notes: "",
  company_name: "",
  contact_name: "",
  phone_number: "",
};

const submitSuccessMessage = "投稿しました。案件一覧に掲載されました。";

const deliveryJobCategoryOptions = [
  { value: "spot", label: "スポット便" },
  { value: "charter", label: "チャーター" },
  { value: "regular", label: "定期便" },
  { value: "work", label: "常用" },
  { value: "other", label: "その他" },
] as const;

const otherJobCategoryOptions = [
  { value: "regular", label: "定期便" },
  { value: "driver_recruitment", label: "ドライバー募集" },
  { value: "referral_request", label: "案件紹介依頼" },
  { value: "other", label: "その他" },
] as const;

export function JobSubmissionPage({ profile, sessionId, onNavigateToJobs }: Props) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [distanceError, setDistanceError] = useState<string | null>(null);
  const [distanceResult, setDistanceResult] = useState<DistanceMeasureResult | null>(null);
  const [distanceLoading, setDistanceLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const navigateTimerRef = useRef<number | null>(null);

  const apiUrlMissing = useMemo(() => !webEnv.apiBaseUrl, []);
  const disabledReason = saving
    ? "送信中のため、完了までお待ちください。"
    : submitted
      ? "投稿済みです。もう一件投稿する場合は下のボタンを押してください。"
      : null;

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (["pickup_prefecture", "pickup_city", "pickup_address", "delivery_prefecture", "delivery_city", "delivery_address", "vehicle_type", "price"].includes(field)) {
      if (distanceResult) {
        setDistanceError("車種・住所・運賃を変更したため、距離・標準運賃を再計算してください。");
      } else {
        setDistanceError(null);
      }
      setDistanceResult(null);
    }
  };

  const switchPostingType = (postingType: "delivery" | "other") => {
    setForm((current) => ({
      ...current,
      posting_type: postingType,
      job_category:
        postingType === "delivery"
          ? deliveryJobCategoryOptions.some((option) => option.value === current.job_category)
            ? current.job_category
            : "spot"
          : otherJobCategoryOptions.some((option) => option.value === current.job_category)
            ? current.job_category
            : "other",
      vehicle_type: postingType === "other" ? "" : current.vehicle_type || "軽バン",
    }));
    setDistanceResult(null);
    setDistanceError(null);
  };

  useEffect(() => {
    return () => {
      if (navigateTimerRef.current !== null) {
        window.clearTimeout(navigateTimerRef.current);
      }
    };
  }, []);

  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void handleSubmit();
  };

  const handleButtonClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    void handleSubmit();
  };

  const handleSubmit = async () => {
    setMessage("送信処理を開始しました。");
    setError(null);
    setValidationErrors([]);

    if (submitted) {
      setMessage(submitSuccessMessage);
      return;
    }

    if (saving) {
      setMessage("送信中...");
      return;
    }

    if (apiUrlMissing) {
      setError("API URLが未設定です。VITE_API_BASE_URLを設定してください。");
      return;
    }

    const errors = validateForm(form);
    if (errors.length > 0) {
      setValidationErrors(errors);
      setError("以下を入力してください。");
      return;
    }

    setSaving(true);
    setMessage("送信中...");
    try {
      const response = await submitLiffJob(toPayload(form, profile, sessionId, distanceResult));
      setMessage(submitSuccessMessage);
      setSubmitted(true);
      setSubmittedJobId(typeof response.job.id === "string" ? response.job.id : null);
      setForm(initialForm);
      setDistanceResult(null);
      setDistanceError(null);
      window.scrollTo({ top: 0, behavior: "smooth" });
      if (navigateTimerRef.current !== null) {
        window.clearTimeout(navigateTimerRef.current);
      }
      navigateTimerRef.current = window.setTimeout(onNavigateToJobs, 2000);
    } catch (exc) {
      setError(buildSubmitErrorMessage(exc));
    } finally {
      setSaving(false);
    }
  };

  const handleMeasureDistance = async () => {
    setDistanceError(null);
    setDistanceResult(null);

    if (!canBuildDistanceAddresses(form)) {
      setDistanceError("積地・卸地の都道府県と市区町村を入力してください");
      return;
    }

    if (apiUrlMissing) {
      setDistanceError("API URLが未設定です。VITE_API_BASE_URLを設定してください。");
      return;
    }

    setDistanceLoading(true);
    try {
      const result = await measureDistance({
        pickup_address: buildAddress(form.pickup_prefecture, form.pickup_city, form.pickup_address),
        delivery_address: buildAddress(form.delivery_prefecture, form.delivery_city, form.delivery_address),
        pickup_prefecture: form.pickup_prefecture,
        vehicle_type: form.vehicle_type,
        posted_fare: form.price || null,
        pickup_detail_missing: !form.pickup_address.trim(),
        delivery_detail_missing: !form.delivery_address.trim(),
      });
      setDistanceResult(result);
      if (result.fare_calc_status === "api_key_missing") {
        setDistanceError(result.fare_calc_note ?? "距離取得APIが設定されていません");
      } else if (!result.distance_km) {
        setDistanceError(result.fare_calc_note ?? "距離を取得できませんでした");
      }
    } catch (exc) {
      setDistanceError(exc instanceof Error ? exc.message : "距離を取得できませんでした");
    } finally {
      setDistanceLoading(false);
    }
  };

  const resetForNextSubmission = () => {
    setForm(initialForm);
    setSaving(false);
    setSubmitted(false);
    setSubmittedJobId(null);
    setMessage(null);
    setError(null);
    setValidationErrors([]);
    setDistanceResult(null);
    setDistanceError(null);
    if (navigateTimerRef.current !== null) {
      window.clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main className="page-shell">
      <form className="form-panel" onSubmit={handleFormSubmit} noValidate>
        <div className="form-panel__header">
          <h2>案件投稿</h2>
          <p>投稿後は案件一覧に掲載されます。</p>
        </div>

        {message ? <p className="notice">{message}</p> : null}
        {submittedJobId ? <p className="notice">受付ID: {submittedJobId}</p> : null}
        {error ? <p className="notice notice-error">{error}</p> : null}
        {disabledReason ? <p className="notice notice-warning">{disabledReason}</p> : null}
        {validationErrors.length > 0 ? (
          <div className="notice notice-warning" role="alert">
            <strong>不足している項目</strong>
            <ul className="validation-list">
              {validationErrors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="posting-type-tabs" role="tablist" aria-label="投稿タイプ">
          <button
            type="button"
            className={form.posting_type === "delivery" ? "active" : ""}
            onClick={() => switchPostingType("delivery")}
          >
            通常配送案件
          </button>
          <button
            type="button"
            className={form.posting_type === "other" ? "active" : ""}
            onClick={() => switchPostingType("other")}
          >
            その他案件
          </button>
        </div>

        <div className="form-grid">
          <label>
            <span>案件種別</span>
            <select value={form.job_category} onChange={(event) => update("job_category", event.target.value)}>
              {(form.posting_type === "other" ? otherJobCategoryOptions : deliveryJobCategoryOptions).map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {form.posting_type === "other" ? (
            <>
              <label>
                <span>タイトル *</span>
                <input value={form.title} onChange={(event) => update("title", event.target.value)} />
              </label>
              <label className="form-grid__wide">
                <span>案件本文 *</span>
                <textarea rows={8} value={form.free_text} onChange={(event) => update("free_text", event.target.value)} />
              </label>
              <label>
                <span>対象エリア</span>
                <input value={form.target_area} onChange={(event) => update("target_area", event.target.value)} />
              </label>
              <label>
                <span>稼働日</span>
                <input type="date" value={form.scheduled_date} onChange={(event) => update("scheduled_date", event.target.value)} />
              </label>
              <label>
                <span>稼働時間</span>
                <input value={form.scheduled_time_text} onChange={(event) => update("scheduled_time_text", event.target.value)} />
              </label>
            </>
          ) : (
            <>
          <label>
            <span>積地都道府県 *</span>
            <input value={form.pickup_prefecture} onChange={(event) => update("pickup_prefecture", event.target.value)} />
          </label>
          <label>
            <span>積地市区町村 *</span>
            <input value={form.pickup_city} onChange={(event) => update("pickup_city", event.target.value)} />
          </label>
          <label>
            <span>積地詳細住所</span>
            <input value={form.pickup_address} onChange={(event) => update("pickup_address", event.target.value)} />
          </label>
          <label>
            <span>卸地都道府県 *</span>
            <input value={form.delivery_prefecture} onChange={(event) => update("delivery_prefecture", event.target.value)} />
          </label>
          <label>
            <span>卸地市区町村 *</span>
            <input value={form.delivery_city} onChange={(event) => update("delivery_city", event.target.value)} />
          </label>
          <label>
            <span>卸地詳細住所</span>
            <input value={form.delivery_address} onChange={(event) => update("delivery_address", event.target.value)} />
          </label>
          <label>
            <span>集荷日</span>
            <input type="date" value={form.scheduled_date} onChange={(event) => update("scheduled_date", event.target.value)} />
          </label>
          <label>
            <span>集荷時間</span>
            <input value={form.scheduled_time_text} onChange={(event) => update("scheduled_time_text", event.target.value)} />
          </label>
          <label>
            <span>納品日</span>
            <input type="date" value={form.delivery_date} onChange={(event) => update("delivery_date", event.target.value)} />
          </label>
          <label>
            <span>納品時間</span>
            <input value={form.delivery_time_text} onChange={(event) => update("delivery_time_text", event.target.value)} />
          </label>
            </>
          )}
          <label>
            <span>{form.posting_type === "delivery" ? "車種 *" : "車種"}</span>
            <select value={form.vehicle_type} onChange={(event) => update("vehicle_type", event.target.value)}>
              {form.posting_type === "other" ? <option value="">未指定</option> : null}
              {vehicleTypeOptions.map((vehicleType) => (
                <option value={vehicleType} key={vehicleType}>
                  {vehicleType}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>台数</span>
            <input type="number" min="1" inputMode="numeric" value={form.vehicle_count} onChange={(event) => update("vehicle_count", event.target.value)} />
          </label>
          <label>
            <span>{form.posting_type === "delivery" ? "荷物内容" : "内容メモ"}</span>
            <input value={form.cargo_type} onChange={(event) => update("cargo_type", event.target.value)} />
          </label>
          <label>
            <span>運賃</span>
            <input type="number" min="0" inputMode="numeric" value={form.price} onChange={(event) => update("price", event.target.value)} />
          </label>
          {form.posting_type === "delivery" ? (
          <div className="form-grid__wide distance-measure">
            <p className="notice">
              走行距離・標準運賃目安は概算です。詳細住所が未入力の場合、距離が実際と異なる場合があります。
            </p>
            <button type="button" className="form-submit" onClick={handleMeasureDistance} disabled={distanceLoading}>
              {distanceLoading ? "距離を取得中..." : "距離を測る"}
            </button>
            {distanceError ? <p className="notice notice-warning">{distanceError}</p> : null}
            {distanceResult && distanceResult.distance_km ? (
              <DistancePreview result={distanceResult} postedFare={form.price} />
            ) : null}
          </div>
          ) : (
            <div className="form-grid__wide distance-measure">
              <p className="notice">その他案件は距離・標準運賃を対象外として投稿できます。</p>
            </div>
          )}
          <label>
            <span>税区分</span>
            <select value={form.tax_type} onChange={(event) => update("tax_type", event.target.value)}>
              <option value="税別">税別</option>
              <option value="税込">税込</option>
              <option value="不明">不明</option>
            </select>
          </label>
          <label>
            <span>高速代</span>
            <input value={form.highway_fee_note} onChange={(event) => update("highway_fee_note", event.target.value)} />
          </label>
          <label>
            <span>手数料メモ</span>
            <input value={form.fee_note} onChange={(event) => update("fee_note", event.target.value)} />
          </label>
          <label>
            <span>会社名 *</span>
            <input value={form.company_name} onChange={(event) => update("company_name", event.target.value)} />
          </label>
          <label>
            <span>担当者名 *</span>
            <input value={form.contact_name} onChange={(event) => update("contact_name", event.target.value)} />
          </label>
          <label>
            <span>電話番号 *</span>
            <input value={form.phone_number} onChange={(event) => update("phone_number", event.target.value)} />
          </label>
          <label className="form-grid__wide">
            <span>備考</span>
            <textarea rows={4} value={form.notes} onChange={(event) => update("notes", event.target.value)} />
          </label>
        </div>

        {submitted ? (
          <div className="success-actions">
            <button type="button" className="primary-action form-submit" onClick={onNavigateToJobs}>
              <ListChecks aria-hidden="true" size={16} />
              案件一覧を見る
            </button>
            <button type="button" className="form-submit" onClick={resetForNextSubmission}>
              <RotateCcw aria-hidden="true" size={16} />
              もう一件投稿する
            </button>
            {profile.inClient ? (
              <button type="button" className="form-submit" onClick={closeLiffWindow}>
                <X aria-hidden="true" size={16} />
                閉じる
              </button>
            ) : null}
          </div>
        ) : null}

        <button type="submit" className="primary-action form-submit" onClick={handleButtonClick} disabled={saving || submitted}>
          <Send aria-hidden="true" size={16} />
          {saving ? "送信中..." : "投稿する"}
        </button>
      </form>
    </main>
  );
}

function toPayload(
  form: typeof initialForm,
  profile: LiffProfileState,
  sessionId: string | null,
  distance: DistanceMeasureResult | null,
): LiffJobPayload {
  const isOtherPosting = form.posting_type === "other";
  return {
    posting_type: form.posting_type as LiffJobPayload["posting_type"],
    job_category: form.job_category as LiffJobPayload["job_category"],
    title: form.title.trim() || null,
    free_text: form.free_text.trim() || null,
    target_area: form.target_area.trim() || null,
    pickup_prefecture: isOtherPosting ? null : form.pickup_prefecture,
    pickup_city: isOtherPosting ? null : form.pickup_city,
    pickup_address: isOtherPosting ? null : form.pickup_address || null,
    delivery_prefecture: isOtherPosting ? null : form.delivery_prefecture,
    delivery_city: isOtherPosting ? null : form.delivery_city,
    delivery_address: isOtherPosting ? null : form.delivery_address || null,
    scheduled_date: form.scheduled_date || null,
    scheduled_time_text: form.scheduled_time_text || null,
    delivery_date: form.delivery_date || null,
    delivery_time_text: form.delivery_time_text || null,
    vehicle_type: form.vehicle_type || null,
    vehicle_count: Number(form.vehicle_count || 1),
    cargo_type: form.cargo_type || null,
    price: form.price ? Number(form.price) : null,
    posted_fare_yen: distance?.posted_fare_yen ?? (form.price ? Number(form.price) : null),
    tax_type: form.tax_type as LiffJobPayload["tax_type"],
    highway_fee_note: form.highway_fee_note || null,
    fee_note: form.fee_note || null,
    notes: form.notes || null,
    distance_km: distance?.distance_km ?? null,
    distance_text: distance?.distance_text ?? null,
    distance_source: distance?.distance_source ?? null,
    standard_fare_yen: distance?.standard_fare_yen ?? null,
    fare_ratio_percent: distance?.fare_ratio_percent ?? null,
    fare_ratio_text: distance?.fare_ratio_text ?? null,
    fare_judgement: distance?.fare_judgement ?? null,
    fare_calc_status: distance?.fare_calc_status ?? (isOtherPosting ? "not_applicable" : "not_calculated"),
    fare_calc_note: distance?.fare_calc_note ?? (isOtherPosting ? "積地・卸地を指定しない案件のため" : null),
    fare_region: distance?.fare_region ?? null,
    fare_vehicle_class: distance?.fare_vehicle_class ?? null,
    fare_vehicle_label: distance?.fare_vehicle_label ?? null,
    company_name: form.company_name.trim(),
    contact_name: form.contact_name.trim(),
    phone_number: form.phone_number.trim(),
    line_user_id: profile.userId || null,
    display_name: profile.displayName || null,
    session_id: sessionId || null,
  };
}

function DistancePreview({ result, postedFare }: { result: DistanceMeasureResult; postedFare: string }) {
  return (
    <section className="distance-preview" aria-label="距離と標準運賃プレビュー">
      <dl>
        <div>
          <dt>走行距離</dt>
          <dd>{result.distance_text ?? "未取得"}</dd>
        </div>
        <div>
          <dt>算出区分</dt>
          <dd>{result.fare_vehicle_label ?? "未計算"}</dd>
        </div>
        <div>
          <dt>運輸局</dt>
          <dd>{transportRegionLabel(result.fare_region)}</dd>
        </div>
        <div>
          <dt>標準運賃目安</dt>
          <dd>{formatOptionalYen(result.standard_fare_yen)}</dd>
        </div>
        <div>
          <dt>投稿運賃</dt>
          <dd>{formatPrice(postedFare ? Number(postedFare) : null)}</dd>
        </div>
        <div>
          <dt>標準比</dt>
          <dd>{result.fare_ratio_text ?? "未計算"}</dd>
        </div>
        <div>
          <dt>判定</dt>
          <dd>{result.fare_judgement ?? "未計算"}</dd>
        </div>
      </dl>
      <p>
        標準運賃目安は、一般貨物は令和6年3月告示の標準的な運賃、軽貨物は貨物軽自動車運送事業運賃料金表をもとにした概算です。実際の契約運賃とは異なる場合があります。
      </p>
    </section>
  );
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

function formatOptionalYen(value: number | null | undefined): string {
  return value != null ? formatPrice(value) : "未計算";
}

function canBuildDistanceAddresses(form: typeof initialForm): boolean {
  return Boolean(
    form.pickup_prefecture.trim() &&
      form.pickup_city.trim() &&
      form.delivery_prefecture.trim() &&
      form.delivery_city.trim(),
  );
}

function buildAddress(prefecture: string, city: string, address: string): string {
  return [prefecture, city, address]
    .map((value) => value.trim())
    .filter((value) => value && value !== "未入力")
    .join("");
}

function validateForm(form: typeof initialForm): string[] {
  const errors: string[] = [];
  if (form.posting_type === "delivery") {
    if (!form.pickup_prefecture.trim()) errors.push("積地都道府県");
    if (!form.pickup_city.trim()) errors.push("積地市区町村");
    if (!form.delivery_prefecture.trim()) errors.push("卸地都道府県");
    if (!form.delivery_city.trim()) errors.push("卸地市区町村");
    if (!form.vehicle_type.trim()) errors.push("車種");
  } else {
    if (!form.title.trim()) errors.push("タイトル");
    if (!form.free_text.trim()) errors.push("案件本文");
  }
  if (!form.company_name.trim()) errors.push("会社名");
  if (!form.contact_name.trim()) errors.push("担当者名");
  if (!form.phone_number.trim()) errors.push("電話番号");
  return errors;
}

function buildSubmitErrorMessage(exc: unknown): string {
  if (exc instanceof Error && exc.message.includes("API接続に失敗")) {
    return exc.message;
  }
  if (exc instanceof Error && exc.message.includes("入力データの形式")) {
    return exc.message;
  }
  if (exc instanceof Error && exc.message.includes("保存に失敗")) {
    return exc.message;
  }
  if (exc instanceof Error && exc.message.includes("Supabase保存エラー")) {
    return exc.message;
  }
  if (exc instanceof Error && exc.message.includes("DBカラム不一致")) {
    return exc.message;
  }
  if (exc instanceof Error && exc.message.includes("source_type制約")) {
    return exc.message;
  }
  return "投稿に失敗しました。もう一度お試しください。";
}
