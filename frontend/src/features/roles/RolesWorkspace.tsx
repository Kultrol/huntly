import { useRef, useState } from "react";
import { PencilIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LoadError, LoadingState } from "@/components/feedback/LoadState";
import { useCompanies } from "@/features/companies/useCompanies";
import { RoleEvents } from "@/features/events/RoleEvents";
import { UpcomingEventsCard } from "@/features/events/UpcomingEventsCard";
import { AgingRolesCard } from "./AgingRolesCard";
import { RoleDetails } from "./RoleDetails";
import { RoleDialog, type RoleEditor } from "./RoleDialog";
import { RolesTable } from "./RolesTable";
import { useRoles } from "./useRoles";
import type { TrackedRole } from "./types";

export default function RolesWorkspace({ userId }: { userId: string }) {
  const { load, retry, save, remove } = useRoles(userId);
  const [companyList, reloadCompanies] = useCompanies();
  const companies = new Map(companyList.records.map(({ id, name }) => [id, name]));
  const [editor, setEditor] = useState<RoleEditor | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [eventVersion, setEventVersion] = useState(0);
  const [focusRequest, setFocusRequest] = useState(0);
  const opener = useRef<HTMLButtonElement | null>(null);
  const workspace = useRef<HTMLDivElement>(null);
  const roles = load.status === "ready" ? load.roles : [];

  function retryRoles() {
    retry();
    if (companyList.status === "error") reloadCompanies();
  }

  function openRole(id: string) {
    setSearch("");
    setStatus("");
    setSelectedId(id);
    setFocusRequest((value) => value + 1);
  }

  function openEditor(next: RoleEditor, button: HTMLButtonElement) {
    opener.current = button;
    setEditor(next);
  }

  function handleRoleSaved(role: TrackedRole) {
    if (editor?.mode === "create") openRole(role.id);
    setEditor(null);
  }

  function refreshEvents() {
    setEventVersion((value) => value + 1);
  }

  async function handleRoleDeleted(id: string) {
    await remove(id);
    setSelectedId(null);
    refreshEvents();
  }

  function restoreEditorFocus() {
    if (opener.current?.isConnected) return opener.current;
    return workspace.current?.querySelector("button") ?? null;
  }

  return (
    <div ref={workspace} className="space-y-6">
      <h1 className="sr-only">Roles</h1>
      <div className="grid gap-4 @3xl/workspace:grid-cols-2">
        <UpcomingEventsCard
          userId={userId}
          roles={roles}
          version={eventVersion}
          onSelectRole={openRole}
        />
        {load.status === "ready" ? (
          <AgingRolesCard roles={roles} onSelect={openRole} />
        ) : (
          <Skeleton className="min-h-40 rounded-xl" />
        )}
      </div>
      {load.status === "loading" && <LoadingState message="Loading roles…" />}
      {load.status === "error" && <LoadError message={load.message} onRetry={retryRoles} retryLabel="Retry roles" />}
      {load.status === "ready" && companyList.status === "error" && (
        <LoadError message={`Could not load company names. ${companyList.error}`} onRetry={reloadCompanies} retryLabel="Retry companies" />
      )}
      {load.status === "ready" && (
        <RolesTable
          roles={roles}
          companies={companies}
          search={search}
          status={status}
          onSearch={setSearch}
          onStatus={setStatus}
          selectedId={selectedId}
          focusRequest={focusRequest}
          onSelect={setSelectedId}
          onCreate={(button) => openEditor({ mode: "create" }, button)}
          renderDetails={(role) => (
            <>
              <div className="mb-5 flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(event) => openEditor({ mode: "edit", role }, event.currentTarget)}
                >
                  <PencilIcon aria-hidden="true" />
                  Edit role
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(event) => openEditor({ mode: "delete", role }, event.currentTarget)}
                >
                  Delete role
                </Button>
              </div>
              <div className="grid gap-6 @4xl/role:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
                <RoleDetails
                  role={role}
                  companyName={role.company_id ? companies.get(role.company_id) : undefined}
                />
                <RoleEvents
                  key={role.id}
                  userId={userId}
                  roleId={role.id}
                  roleTitle={role.title}
                  version={eventVersion}
                  onChanged={refreshEvents}
                />
              </div>
            </>
          )}
        />
      )}
      {editor && (
        <RoleDialog
          editor={editor}
          companies={companyList}
          reloadCompanies={reloadCompanies}
          onClose={() => setEditor(null)}
          onSave={save}
          onSaved={handleRoleSaved}
          onDelete={handleRoleDeleted}
          restoreFocus={restoreEditorFocus}
        />
      )}
    </div>
  );
}
