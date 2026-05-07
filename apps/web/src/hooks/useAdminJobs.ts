import { useCallback, useEffect, useState } from "react";

import { fetchAdminJobs } from "../lib/adminApi";
import type { Job } from "../types/job";

export function useAdminJobs(idToken: string | null) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchAdminJobs(idToken);
      setJobs(data);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "案件一覧の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [idToken]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  return { jobs, loading, error, reload: loadJobs, setJobs };
}
