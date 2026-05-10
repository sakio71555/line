import { Send } from "lucide-react";
import { useState } from "react";

import { submitLiffVehicleAvailability, type LiffVehiclePayload } from "../lib/liffApi";
import type { LiffProfileState } from "../lib/liff";
import { vehicleTypeOptions } from "../constants/vehicleTypes";

type Props = {
  profile: LiffProfileState;
};

const initialForm = {
  prefecture: "",
  city: "",
  vehicle_type: "軽バン",
  available_from: "",
  company_name: "",
  contact_name: "",
  phone_number: "",
  notes: "",
};

export function VehicleAvailabilityPage({ profile }: Props) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = async () => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await submitLiffVehicleAvailability(toPayload(form, profile));
      setMessage("空車情報を登録しました。管理者確認後に活用されます。");
      setForm(initialForm);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "空車登録に失敗しました。");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="page-shell">
      <section className="form-panel">
        <div className="form-panel__header">
          <h2>空車登録</h2>
          <p>空車情報は案件とは別に保存します。</p>
        </div>

        {message ? <p className="notice">{message}</p> : null}
        {error ? <p className="notice notice-error">{error}</p> : null}

        <div className="form-grid">
          <label>
            <span>現在地都道府県</span>
            <input value={form.prefecture} onChange={(event) => update("prefecture", event.target.value)} />
          </label>
          <label>
            <span>現在地市区町村</span>
            <input value={form.city} onChange={(event) => update("city", event.target.value)} />
          </label>
          <label>
            <span>車種</span>
            <select value={form.vehicle_type} onChange={(event) => update("vehicle_type", event.target.value)}>
              {vehicleTypeOptions.map((vehicleType) => (
                <option value={vehicleType} key={vehicleType}>
                  {vehicleType}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>空車開始日時</span>
            <input type="datetime-local" value={form.available_from} onChange={(event) => update("available_from", event.target.value)} />
          </label>
          <label>
            <span>会社名</span>
            <input value={form.company_name} onChange={(event) => update("company_name", event.target.value)} />
          </label>
          <label>
            <span>担当者名</span>
            <input value={form.contact_name} onChange={(event) => update("contact_name", event.target.value)} />
          </label>
          <label>
            <span>電話番号</span>
            <input value={form.phone_number} onChange={(event) => update("phone_number", event.target.value)} />
          </label>
          <label className="form-grid__wide">
            <span>備考</span>
            <textarea rows={4} value={form.notes} onChange={(event) => update("notes", event.target.value)} />
          </label>
        </div>

        <button type="button" className="primary-action form-submit" onClick={submit} disabled={saving}>
          <Send aria-hidden="true" size={16} />
          登録する
        </button>
      </section>
    </main>
  );
}

function toPayload(form: typeof initialForm, profile: LiffProfileState): LiffVehiclePayload {
  return {
    prefecture: form.prefecture,
    city: form.city,
    vehicle_type: form.vehicle_type,
    available_from: form.available_from || null,
    company_name: form.company_name || null,
    contact_name: form.contact_name || null,
    phone_number: form.phone_number || null,
    notes: form.notes || null,
    line_user_id: profile.userId,
  };
}
