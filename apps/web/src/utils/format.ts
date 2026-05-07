export function formatDate(value: string | null): string {
  if (!value) return "日付未定";

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).format(date);
}

export function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatPrice(value: number | null): string {
  if (value == null) return "運賃未定";

  return `${new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: 0,
  }).format(value)}円`;
}
