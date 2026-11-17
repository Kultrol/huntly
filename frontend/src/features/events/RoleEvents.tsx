import { useRef, useState } from "react";
import { PlusIcon } from "lucide-react";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";
import { Button } from "@/components/ui/button";
import { EmptyState, LoadError, LoadingState } from "@/components/feedback/LoadState";
import { saveEvent } from "./api";
import { EventDialog, type EventEditor } from "./EventDialog";
import { compareEventDates } from "./eventDates";
import { EventList } from "./EventList";
import { useEvents } from "./useEvents";
import type { RoleEvent } from "./types";

type RoleEventsProps = {
  userId: string;
  roleId: string;
  roleTitle: string;
  version: number;
  onChanged: () => void;
};

export function RoleEvents({ userId, roleId, roleTitle, version, onChanged }: RoleEventsProps) {
  const { request } = useAuth();
  const opener = useRef<HTMLButtonElement | null>(null);
  const addButton = useRef<HTMLButtonElement | null>(null);
  const { events, loading, error, retry } = useEvents(userId, roleId, version);
  const [editor, setEditor] = useState<EventEditor | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const ordered = [...events].sort(compareEventDates);
  const active = ordered.filter((event) => event.status === "pending" || event.status === "scheduled");
  const history = ordered.filter((event) => event.status !== "pending" && event.status !== "scheduled").reverse();

  function openEditor(next: EventEditor, trigger: HTMLButtonElement) {
    opener.current = trigger;
    setCompletionError(null);
    setEditor(next);
  }

  async function completeEvent(event: RoleEvent) {
    if (completing) return;
    setCompleting(true);
    setCompletionError(null);
    try {
      await saveEvent(request, roleId, { status: "completed" }, event.id);
      // Wait for the pending state to release the button before restoring focus.
      window.setTimeout(() => addButton.current?.focus(), 0);
      onChanged();
    } catch (error) {
      setCompletionError(getErrorMessage(error));
    } finally {
      setCompleting(false);
    }
  }

  const listProps = {
    pending: completing || loading,
    onEdit: (event: RoleEvent, trigger: HTMLButtonElement) => openEditor({ mode: "edit", event }, trigger),
    onDelete: (event: RoleEvent, trigger: HTMLButtonElement) => openEditor({ mode: "delete", event }, trigger),
    onComplete: (event: RoleEvent) => void completeEvent(event),
  };

  return (
    <section aria-label="Role events" className="min-w-0 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="section-title">Events</h3>
        <Button
          ref={addButton}
          size="sm"
          variant="outline"
          disabled={completing}
          onClick={(event) => openEditor({ mode: "create" }, event.currentTarget)}
        >
          <PlusIcon aria-hidden="true" />
          Add event
        </Button>
      </div>
      {loading && <LoadingState message="Loading events…" />}
      {error && <LoadError message={error} onRetry={retry} retryLabel="Retry events" />}
      {completionError && !editor && <p role="alert" className="text-destructive">{completionError}</p>}
      {!loading && !error && (
        <>
          {!events.length && <EmptyState message="No events for this role yet." />}
          <EventList events={active} {...listProps} />
          {history.length > 0 && (
            <details className="border-t pt-3">
              <summary className="touch-target cursor-pointer content-center rounded-md text-sm font-medium focus-visible:outline-2 focus-visible:outline-ring">
                Completed and closed ({history.length})
              </summary>
              <div className="pt-3"><EventList events={history} {...listProps} /></div>
            </details>
          )}
        </>
      )}
      {editor && (
        <EventDialog
          editor={editor}
          roleId={roleId}
          roleTitle={roleTitle}
          onClose={() => setEditor(null)}
          onChanged={onChanged}
          restoreFocus={() => opener.current?.isConnected ? opener.current : addButton.current}
        />
      )}
    </section>
  );
}
