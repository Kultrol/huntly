import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/api/client";
import type { AuthContextValue } from "@/features/auth/session/AuthContext";

export type Dataset<T> =
  | { status: "loading"; records: T[]; error: null }
  | { status: "ready"; records: T[]; error: null }
  | { status: "error"; records: T[]; error: string };

const loadingDataset: Dataset<never> = { status: "loading", records: [], error: null };

type DatasetResult<T> = {
  path: string;
  sessionKey: string;
  version: number;
  dataset: Dataset<T>;
};

export function useDataset<T>(
  path: string,
  { user, csrfToken, request }: AuthContextValue,
  readRecords: (body: unknown, userId: string) => T[],
) {
  const userId = user?.id;
  const sessionKey = userId ? `${userId}:${csrfToken ?? ""}` : null;
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState<DatasetResult<T> | null>(null);

  useEffect(() => {
    if (userId === undefined || sessionKey === null) return;
    const controller = new AbortController();

    async function fetchDataset(key: string, expectedOwner: string) {
      let dataset: Dataset<T>;
      try {
        const response = await request(path, { signal: controller.signal });
        const records = readRecords(await response.json(), expectedOwner);
        dataset = { status: "ready", records, error: null };
      } catch (error) {
        dataset = { status: "error", records: [], error: getErrorMessage(error) };
      }

      if (!controller.signal.aborted) setResult({ path, sessionKey: key, version, dataset });
    }

    void fetchDataset(sessionKey, userId);
    return () => controller.abort();
  }, [path, readRecords, request, sessionKey, userId, version]);

  // Hide results from an earlier session or attempt before the next request starts.
  const dataset = result?.sessionKey === sessionKey && result.version === version && result.path === path
    ? result.dataset
    : loadingDataset;
  const retry = useCallback(() => setVersion((currentVersion) => currentVersion + 1), []);

  // Apply a confirmed write in place so a mounted list keeps its scroll and focus.
  function updateRecords(update: (records: T[]) => T[]) {
    if (dataset.status !== "ready") {
      retry();
      return;
    }
    setResult((current) => {
      if (current?.path !== path || current.sessionKey !== sessionKey || current.version !== version
        || current.dataset.status !== "ready") return current;
      return { ...current, dataset: { ...current.dataset, records: update(current.dataset.records) } };
    });
  }

  return [dataset, retry, updateRecords] as const;
}
