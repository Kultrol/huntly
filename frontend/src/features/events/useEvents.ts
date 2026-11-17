import { useEffect, useState } from "react";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";
import { listRoleEvents, listUpcomingEvents } from "./api";
import { localToday } from "./eventDates";
import type { RoleEvent } from "./types";

export function useEvents(userId: string, roleId: string | null, version = 0) {
  const { request } = useAuth();
  const [events, setEvents] = useState<RoleEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const today = localToday();

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const records = roleId
          ? await listRoleEvents(request, roleId, controller.signal)
          : await listUpcomingEvents(request, userId, today, controller.signal);
        if (!controller.signal.aborted) setEvents(records);
      } catch (error) {
        if (!controller.signal.aborted) setError(getErrorMessage(error));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [today, roleId, userId, request, version, attempt]);

  return { events, loading, error, retry: () => setAttempt((value) => value + 1) };
}
