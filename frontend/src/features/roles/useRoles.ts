import { useEffect, useState } from "react";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";
import { deleteRole, listRoleCompanies, listRoles, saveRole } from "./api";
import type { RoleChange, TrackedRole } from "./types";

type RolesLoad =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; roles: TrackedRole[] };

export function useRoles(userId: string) {
  const { request } = useAuth();
  const [load, setLoad] = useState<RolesLoad>({ status: "loading" });
  const [companies, setCompanies] = useState<ReadonlyMap<string, string>>(new Map());
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

    async function loadCompanyNames() {
      try {
        const names = await listRoleCompanies(request, userId, signal);
        if (!signal.aborted) setCompanies(names);
      } catch {
        // Roles are still usable if company names are temporarily unavailable.
        if (!signal.aborted) setCompanies(new Map());
      }
    }

    void loadRoles();
    void loadCompanyNames();
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

  return { load, companies, retry, save, remove };
}
