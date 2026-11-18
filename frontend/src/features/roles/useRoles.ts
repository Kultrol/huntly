import { useEffect, useState } from "react";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";
import { deleteRole, listRoles, saveRole } from "./api";
import type { RoleChange, TrackedRole } from "./types";

type RolesLoad =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; roles: TrackedRole[] };

export function useRoles(userId: string) {
  const { request } = useAuth();
  const [load, setLoad] = useState<RolesLoad>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    async function loadRoles() {
      try {
        const roles = await listRoles(request, userId, signal);
        if (!signal.aborted) setLoad({ status: "ready", roles });
      } catch (error) {
        if (!signal.aborted) setLoad({ status: "error", message: getErrorMessage(error) });
      }
    }

    void loadRoles();
    return () => controller.abort();
  }, [request, userId, attempt]);

  function retry() {
    setLoad({ status: "loading" });
    setAttempt((current) => current + 1);
  }

  async function save(change: RoleChange) {
    const saved = await saveRole(request, userId, change);
    setLoad((current) => {
      if (current.status !== "ready") return current;
      return {
        status: "ready",
        roles: [saved, ...current.roles.filter((role) => role.id !== saved.id)],
      };
    });
    return saved;
  }

  async function remove(id: string) {
    await deleteRole(request, id);
    setLoad((current) => current.status === "ready"
      ? { status: "ready", roles: current.roles.filter((role) => role.id !== id) }
      : current);
  }

  return { load, retry, save, remove };
}
