import { EyeOff, Pencil, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminJobEditor } from "../components/AdminJobEditor";
import { JobCard } from "../components/JobCard";
import {
  applyStatusUpdateCandidate,
  fetchAdminLineMessages,
  fetchStatusUpdateCandidates,
  hideAdminJob,
  ignoreStatusUpdateCandidate,
  type AdminJobUpdatePayload,
  updateAdminJob,
  verifyAdminJob,
} from "../lib/adminApi";
import type { LiffProfileState } from "../lib/liff";
import { useAdminJobs } from "../hooks/useAdminJobs";
import {
  jobStatusLabels,
  type Job,
  type JobFilters,
  type JobStatusUpdateCandidate,
  type LineMessage,
} from "../types/job";

type Props = {
  filters: JobFilters;
  profile: LiffProfileState;
};

export function AdminJobsPage({ filters, profile }: Props) {
  const { jobs, loading, error, reload, setJobs } = useAdminJobs(profile.idToken);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [statusUpdates, setStatusUpdates] = useState<JobStatusUpdateCandidate[]>([]);
  const [lineMessages, setLineMessages] = useState<LineMessage[]>([]);
  const [statusUpdatesError, setStatusUpdatesError] = useState<string | null>(null);
  const [lineMessagesError, setLineMessagesError] = useState<string | null>(null);
  const [lineMessagesOpen, setLineMessagesOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const adminContext = useMemo(
    () => ({ idToken: profile.idToken }),
    [profile.idToken],
  );

  const filteredJobs = useMemo(() => filterAdminJobs(jobs, filters), [jobs, filters]);
  const reviewJobs = useMemo(
    () => jobs.filter((job) => matchesAdminSearch(job, filters)).filter(isReviewJob).sort(sortAdminJobs),
    [jobs, filters],
  );
  const otherJobs = useMemo(() => filteredJobs.filter((job) => !isReviewJob(job)), [filteredJobs]);
  const lineReviewMessages = useMemo(() => filterLineReviewMessages(lineMessages), [lineMessages]);
  const priorityLineMessages = useMemo(
    () => lineReviewMessages.filter(isPriorityLineMessage),
    [lineReviewMessages],
  );
  const lowPriorityLineMessages = useMemo(
    () => lineReviewMessages.filter((message) => !isPriorityLineMessage(message)),
    [lineReviewMessages],
  );
  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? null;

  const loadStatusUpdates = useCallback(async () => {
    setStatusUpdatesError(null);
    try {
      setStatusUpdates(await fetchStatusUpdateCandidates(adminContext));
    } catch (exc) {
      setStatusUpdatesError(errorMessage(exc, "終了報告候補の取得に失敗しました"));
    }
  }, [adminContext]);

  const loadLineMessages = useCallback(async () => {
    setLineMessagesError(null);
    if (!profile.idToken) {
      setLineMessages([]);
      setLineMessagesError("管理画面はLINE内で開いてください");
      return;
    }
    try {
      setLineMessages(await fetchAdminLineMessages());
    } catch {
      setLineMessagesError("LINE原本の取得に失敗しました");
    }
  }, [profile.idToken]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    void loadStatusUpdates();
    void loadLineMessages();
  }, [loadLineMessages, loadStatusUpdates]);

  const replaceJob = (updatedJob: Job) => {
    setJobs((current) =>
      current
        .map((job) => (job.id === updatedJob.id ? updatedJob : job))
        .sort(sortAdminJobs),
    );
  };

  const reloadAll = () => {
    setActionError(null);
    void reload();
    void loadStatusUpdates();
    void loadLineMessages();
  };

  const runAction = async (action: () => Promise<Job>) => {
    setSaving(true);
    setActionError(null);
    try {
      replaceJob(await action());
    } catch (exc) {
      setActionError(errorMessage(exc, "案件の更新に失敗しました"));
    } finally {
      setSaving(false);
    }
  };

  const handleSave = (payload: AdminJobUpdatePayload) => {
    if (!selectedJobId) return;
    void runAction(() => updateAdminJob(selectedJobId, payload, adminContext));
  };

  const handleVerify = (jobId: string) => {
    void runAction(() => verifyAdminJob(jobId, adminContext));
  };

  const handleHide = (jobId: string) => {
    void runAction(() => hideAdminJob(jobId, adminContext));
  };

  const handleApplyStatusUpdate = (
    statusUpdate: JobStatusUpdateCandidate,
    newStatus: "assigned" | "completed" | "cancelled",
  ) => {
    const targetJobId = statusUpdate.possible_job_id ?? statusUpdate.candidates?.[0]?.id ?? null;
    if (!targetJobId) {
      setActionError("候補案件が未特定です。案件に紐づいている終了報告だけ反映できます。");
      return;
    }
    void runAction(async () => {
      const result = await applyStatusUpdateCandidate(statusUpdate.id, {
        job_id: targetJobId,
        new_status: newStatus,
        reason: "LINE終了報告を確認",
        changed_by_name: "admin",
      }, adminContext);
      setStatusUpdates((current) => current.filter((item) => item.id !== statusUpdate.id));
      return result.job;
    });
  };

  const handleIgnoreStatusUpdate = (statusUpdateId: string) => {
    setSaving(true);
    setActionError(null);
    ignoreStatusUpdateCandidate(statusUpdateId, { reviewed_by: "admin" }, adminContext)
      .then(() => {
        setStatusUpdates((current) => current.filter((item) => item.id !== statusUpdateId));
      })
      .catch((exc) => {
        setActionError(errorMessage(exc, "終了報告候補の更新に失敗しました"));
      })
      .finally(() => setSaving(false));
  };

  return (
    <main className="page-shell">
      <section className="admin-toolbar">
        <div>
          <h2>管理ビュー</h2>
          <p>自分が投稿した案件だけを表示・管理します。</p>
        </div>
        <button type="button" onClick={reloadAll}>
          <RefreshCw aria-hidden="true" size={16} strokeWidth={2.5} />
          更新
        </button>
      </section>

      <section className="admin-stats" aria-label="管理件数">
        <div>
          <span>確認待ち案件</span>
          <strong>{loading ? "-" : `${reviewJobs.length}件`}</strong>
        </div>
        <div>
          <span>終了報告候補</span>
          <strong>{`${statusUpdates.length}件`}</strong>
        </div>
        <div>
          <span>LINE確認項目</span>
          <strong>{`${lineReviewMessages.length}件`}</strong>
        </div>
      </section>

      {!profile.idToken ? (
        <p className="notice notice-warning">自分の投稿を確認するにはLINE内で開き直してください。</p>
      ) : null}

      {actionError ? <p className="notice notice-error">{actionError}</p> : null}

      <section className="status-updates-panel">
        <div className="status-updates-panel__header">
          <div>
            <h2>終了報告候補</h2>
            <p>LINE上の「決まりました」「完了しました」はここで確認してから反映します。</p>
          </div>
          <button type="button" onClick={loadStatusUpdates}>
            <RefreshCw aria-hidden="true" size={16} strokeWidth={2.5} />
            更新
          </button>
        </div>
        {statusUpdatesError ? <p className="notice notice-error">{statusUpdatesError}</p> : null}
        {statusUpdates.length === 0 && !statusUpdatesError ? (
          <p className="empty-state status-updates-panel__empty">未確認の終了報告候補はありません。</p>
        ) : null}
        {statusUpdates.length > 0 ? (
          <div className="status-update-list">
            {statusUpdates.map((update) => (
              <article className="status-update-card" key={update.id}>
                <div className="status-update-card__body">
                  <strong>{displayStatusUpdateText(update.raw_text)}</strong>
                  {hasHiddenInternalPrefix(update.raw_text) ? (
                    <details className="status-update-internal">
                      <summary>詳細を見る</summary>
                      <span>{firstLine(update.raw_text)}</span>
                    </details>
                  ) : null}
                  <dl className="status-update-card__details">
                    <div>
                      <dt>提案</dt>
                      <dd>{update.proposed_status ? jobStatusLabels[update.proposed_status] : "未定"}</dd>
                    </div>
                    <div>
                      <dt>信頼度</dt>
                      <dd>{formatConfidence(update.confidence)}</dd>
                    </div>
                    <div>
                      <dt>候補案件</dt>
                      <dd>{candidateSummary(update)}</dd>
                    </div>
                    <div>
                      <dt>報告者</dt>
                      <dd>
                        {update.reported_by_display_name ?? "未取得"} /{" "}
                        {update.is_reported_by_job_owner
                          ? "投稿者本人の終了報告"
                          : "投稿者以外の終了報告"}
                      </dd>
                    </div>
                    <div>
                      <dt>理由</dt>
                      <dd>{update.reason ?? "理由なし"}</dd>
                    </div>
                  </dl>
                </div>
                <div className="status-update-card__actions">
                  <button type="button" onClick={() => handleApplyStatusUpdate(update, "assigned")} disabled={saving}>
                    手配済みにする
                  </button>
                  <button type="button" onClick={() => handleApplyStatusUpdate(update, "completed")} disabled={saving}>
                    完了にする
                  </button>
                  <button type="button" onClick={() => handleApplyStatusUpdate(update, "cancelled")} disabled={saving}>
                    キャンセルにする
                  </button>
                  <button type="button" className="danger-action" onClick={() => handleIgnoreStatusUpdate(update.id)} disabled={saving}>
                    無視
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="status-updates-panel">
        <div className="status-updates-panel__header">
          <div>
            <h2>確認待ち案件</h2>
            <p>管理者確認、連絡先確認、公開判断が必要な案件です。</p>
          </div>
        </div>
        {error ? <p className="notice notice-error">{error}</p> : null}
        {reviewJobs.length === 0 && !error ? (
          <p className="empty-state status-updates-panel__empty">確認待ち案件はありません。</p>
        ) : null}
        {reviewJobs.length > 0 ? (
          <div className="job-list">
            {reviewJobs.map((job) => (
              <AdminJobRow
                key={job.id}
                job={job}
                saving={saving}
                onEdit={() => setSelectedJobId(job.id)}
                onVerify={() => handleVerify(job.id)}
                onHide={() => handleHide(job.id)}
              />
            ))}
          </div>
        ) : null}
      </section>

      <section className="status-updates-panel">
        <div className="status-updates-panel__header">
          <div>
            <h2>公開中・非公開・完了済み案件</h2>
            <p>公開後の案件、非公開、完了済みを確認できます。</p>
          </div>
        </div>
        {otherJobs.length === 0 && !error ? (
          <p className="empty-state status-updates-panel__empty">表示対象の案件はありません。</p>
        ) : null}
        {otherJobs.length > 0 ? (
          <div className="job-list">
            {otherJobs.map((job) => (
              <AdminJobRow
                key={job.id}
                job={job}
                saving={saving}
                onEdit={() => setSelectedJobId(job.id)}
                onVerify={() => handleVerify(job.id)}
                onHide={() => handleHide(job.id)}
              />
            ))}
          </div>
        ) : null}
      </section>

      <section className="status-updates-panel">
        <div className="status-updates-panel__header">
          <div>
            <h2>LINE原本確認</h2>
            <p>添付・取消・ノート・メンバーイベントの確認用です。</p>
          </div>
          <div className="status-updates-panel__actions">
            <button type="button" onClick={() => setLineMessagesOpen((current) => !current)}>
              {lineMessagesOpen ? "閉じる" : "開く"}
            </button>
            <button type="button" onClick={loadLineMessages}>
              <RefreshCw aria-hidden="true" size={16} strokeWidth={2.5} />
              更新
            </button>
          </div>
        </div>
        {lineMessagesError ? <p className="notice notice-error">{lineMessagesError}</p> : null}
        {!lineMessagesOpen ? (
          <p className="line-message-summary">
            確認対象 {lineReviewMessages.length}件。通常は閉じたままで運用できます。
          </p>
        ) : null}
        {lineMessagesOpen && lineReviewMessages.length === 0 && !lineMessagesError ? (
          <p className="empty-state status-updates-panel__empty">確認対象のLINEイベントはありません。</p>
        ) : null}
        {lineMessagesOpen && lineReviewMessages.length > 0 ? (
          <div className="line-message-groups">
            {priorityLineMessages.length > 0 ? (
              <div className="status-update-list">
                {priorityLineMessages.map((message) => (
                  <LineMessageCard message={message} key={message.id} />
                ))}
              </div>
            ) : null}
            {lowPriorityLineMessages.length > 0 ? (
              <details className="line-message-low-priority">
                <summary>低優先イベントを表示（{lowPriorityLineMessages.length}件）</summary>
                <div className="status-update-list">
                  {lowPriorityLineMessages.map((message) => (
                    <LineMessageCard message={message} key={message.id} />
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        ) : null}
      </section>

      {selectedJob ? (
        <AdminJobEditor
          job={selectedJob}
          saving={saving}
          onSave={handleSave}
          onVerify={() => handleVerify(selectedJob.id)}
          onHide={() => handleHide(selectedJob.id)}
          onClose={() => setSelectedJobId(null)}
        />
      ) : null}

    </main>
  );
}

type AdminJobRowProps = {
  job: Job;
  saving: boolean;
  onEdit: () => void;
  onVerify: () => void;
  onHide: () => void;
};

function AdminJobRow({ job, saving, onEdit, onVerify, onHide }: AdminJobRowProps) {
  return (
    <div className="admin-job-row">
      <JobCard job={job} compact />
      <div className="admin-job-row__actions">
        <button type="button" onClick={onEdit}>
          <Pencil aria-hidden="true" size={16} />
          編集
        </button>
        <button type="button" onClick={onVerify} disabled={saving}>
          <ShieldCheck aria-hidden="true" size={16} />
          確認完了
        </button>
        <button
          type="button"
          className="danger-action"
          onClick={onHide}
          disabled={saving || job.status === "hidden"}
        >
          <EyeOff aria-hidden="true" size={16} />
          非公開
        </button>
      </div>
    </div>
  );
}

function LineMessageCard({ message }: { message: LineMessage }) {
  return (
    <article className="status-update-card line-message-card">
      <div>
        <strong>{lineMessageLabel(message)}</strong>
        <p>{lineMessageSummary(message)}</p>
        <p>{lineMessageBody(message)}</p>
        {message.processing_error ? <p className="line-message-card__error">処理エラー: {message.processing_error}</p> : null}
      </div>
      <details className="line-message-details">
        <summary>詳細を見る</summary>
        <dl>
          <div>
            <dt>message type</dt>
            <dd>{message.message_type ?? "-"}</dd>
          </div>
          <div>
            <dt>event type</dt>
            <dd>{message.event_type ?? "-"}</dd>
          </div>
          <div>
            <dt>user</dt>
            <dd>{shortId(message.source_user_id)}</dd>
          </div>
          <div>
            <dt>group</dt>
            <dd>{shortId(message.source_group_id)}</dd>
          </div>
        </dl>
      </details>
    </article>
  );
}

function lineMessageLabel(message: LineMessage): string {
  if (message.processing_error) {
    return "処理エラー";
  }
  if (message.message_type === "irrelevant" && message.raw_text) {
    return "案件化されなかったテキスト";
  }
  if (message.message_type === "attachment") {
    return `添付確認待ち: ${message.attachment_type ?? "file"}`;
  }
  if (message.message_type === "unsend_event" || message.is_unsent) {
    return "送信取消";
  }
  if (message.message_type === "note_event") {
    return "ノートイベント";
  }
  if (message.message_type === "member_event") {
    return "メンバーイベント";
  }
  return "LINEイベント";
}

function lineMessageSummary(message: LineMessage): string {
  const parts = [message.message_type ?? "type未定"];
  const user = shortId(message.source_user_id);
  if (user !== "-") {
    parts.push(`投稿者:${user}`);
  }
  return parts.join(" / ");
}

function lineMessageBody(message: LineMessage): string {
  return message.raw_text ?? message.attachment_file_name ?? message.attachment_type ?? "本文なし";
}

function shortId(value: string | null): string {
  if (!value) return "-";
  return `...${value.slice(-6)}`;
}

function filterLineReviewMessages(messages: LineMessage[]): LineMessage[] {
  return messages
    .filter(shouldShowLineMessage)
    .sort((a, b) => {
      const priority = lineMessagePriority(a) - lineMessagePriority(b);
      if (priority !== 0) return priority;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
}

function shouldShowLineMessage(message: LineMessage): boolean {
  if (message.processing_error) return true;
  if (message.message_type === "irrelevant" && message.raw_text) return true;
  if (message.message_type === "attachment") return true;
  if (message.is_unsent) return true;
  return ["unsend_event", "note_event", "member_event"].includes(message.message_type ?? "");
}

function isPriorityLineMessage(message: LineMessage): boolean {
  return lineMessagePriority(message) < 5;
}

function lineMessagePriority(message: LineMessage): number {
  if (message.processing_error) return 0;
  if (message.message_type === "irrelevant" && message.raw_text) return 1;
  if (message.message_type === "attachment") return 2;
  return 10;
}

function isReviewJob(job: Job): boolean {
  if (job.source_type === "liff_form" && job.status === "open") {
    return false;
  }
  return (
    job.status === "needs_review" ||
    Boolean(job.review_required) ||
    Boolean(job.contact_missing) ||
    job.analysis_status === "form_submitted"
  );
}

function displayStatusUpdateText(rawText: string): string {
  return stripInternalPrefix(rawText) || rawText;
}

function hasHiddenInternalPrefix(rawText: string): boolean {
  return stripInternalPrefix(rawText) !== rawText;
}

function stripInternalPrefix(rawText: string): string {
  const lines = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length <= 1) {
    return rawText.trim();
  }

  let firstNaturalLineIndex = 0;
  while (firstNaturalLineIndex < lines.length && isInternalIdentifierLine(lines[firstNaturalLineIndex])) {
    firstNaturalLineIndex += 1;
  }

  return lines.slice(firstNaturalLineIndex).join("\n").trim() || rawText.trim();
}

function isInternalIdentifierLine(line: string): boolean {
  return (
    /^codex-phase[0-9a-z-_.]+$/i.test(line) ||
    /^codex-phase[0-9a-z-_.]+\.(pdf|docx?|xlsx?|png|jpe?g|gif|webp)$/i.test(line) ||
    /^[UC]phase[0-9a-z-_.]+$/i.test(line)
  );
}

function firstLine(rawText: string): string {
  return rawText.split(/\r?\n/).find((line) => line.trim())?.trim() ?? "";
}

function formatConfidence(value: number | null): string {
  if (value == null) return "-";
  if (value <= 1) return `${Math.round(value * 100)}%`;
  return `${value}`;
}

function candidateSummary(update: JobStatusUpdateCandidate): string {
  const candidates = update.candidates ?? [];
  if (candidates.length === 0) {
    return update.possible_job_id ? "候補案件あり" : "未特定";
  }
  return candidates
    .map((candidate) => {
      const pickup = candidate.pickup_location ?? "積地未定";
      const delivery = candidate.delivery_location ?? "卸地未定";
      return `${pickup} → ${delivery}`;
    })
    .join(" / ");
}

function filterAdminJobs(jobs: Job[], filters: JobFilters): Job[] {
  return jobs
    .filter((job) => {
      if (!matchesAdminSearch(job, filters)) {
        return false;
      }

      if (filters.status && job.status !== filters.status) {
        return false;
      }

      if (filters.reviewOnly && !job.review_required) {
        return false;
      }

      return true;
    })
    .sort(sortAdminJobs);
}

function matchesAdminSearch(job: Job, filters: JobFilters): boolean {
  const pickupNeedle = filters.pickup.trim();
  if (
    pickupNeedle &&
    !contains(job.pickup_location, pickupNeedle) &&
    !contains(job.pickup_prefecture, pickupNeedle)
  ) {
    return false;
  }

  const deliveryNeedle = filters.delivery.trim();
  if (
    deliveryNeedle &&
    !contains(job.delivery_location, deliveryNeedle) &&
    !contains(job.delivery_prefecture, deliveryNeedle)
  ) {
    return false;
  }

  const vehicleNeedle = filters.vehicleType.trim();
  if (vehicleNeedle && !contains(job.vehicle_type, vehicleNeedle)) {
    return false;
  }

  return true;
}

function contains(value: string | null, needle: string): boolean {
  return value?.toLowerCase().includes(needle.toLowerCase()) ?? false;
}

function sortAdminJobs(a: Job, b: Job): number {
  if (a.status !== b.status) {
    if (a.status === "needs_review") return -1;
    if (b.status === "needs_review") return 1;
  }

  if (a.review_required !== b.review_required) {
    return a.review_required ? -1 : 1;
  }

  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
}

function errorMessage(exc: unknown, fallback: string): string {
  if (exc instanceof Error && exc.message) {
    return exc.message;
  }
  return fallback;
}
