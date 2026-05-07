import { jobStatusLabels, type AnalysisStatus, type JobStatus } from "../types/job";

type Props = {
  status?: JobStatus | AnalysisStatus | null;
  tone?: "job" | "analysis" | "review";
};

export function StatusBadge({ status, tone = "job" }: Props) {
  if (!status) return null;

  const analysisLabels: Record<string, string> = {
    pending: "未解析",
    parsed: "解析済み",
    needs_review: "要確認",
    failed: "解析失敗",
    verified: "確認済み",
    form_submitted: "フォーム投稿",
  };
  const label =
    tone === "analysis"
      ? (analysisLabels[String(status)] ?? status)
      : (jobStatusLabels[status as JobStatus] ?? status);

  return <span className={`badge badge-${tone} badge-${String(status)}`}>{label}</span>;
}
