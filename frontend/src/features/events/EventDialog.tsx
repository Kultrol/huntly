import { useState } from "react";
import { getErrorMessage } from "@/api/client";
import { FormActions } from "@/components/forms/FormActions";
import { FormDialog } from "@/components/forms/FormDialog";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/session/useAuth";
import { deleteEvent, saveEvent } from "./api";
import { EventForm } from "./EventForm";
import { changedEventFields } from "./formValues";
import type { EventInput, RoleEvent } from "./types";

export type EventEditor =
  | { mode: "create" }
  | { mode: "edit" | "delete"; event: RoleEvent };

type EventDialogProps = {
  editor: EventEditor;
  roleId: string;
  roleTitle: string;
  onClose: () => void;
  onChanged: () => void;
  restoreFocus: () => HTMLElement | null;
};

const titles = { create: "Add event", edit: "Edit event", delete: "Delete event?" };

export function EventDialog({
  editor, roleId, roleTitle, onClose, onChanged, restoreFocus,
}: EventDialogProps) {
  const { request } = useAuth();
  const [pending, setPending] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const event = editor.mode === "create" ? undefined : editor.event;

  async function save(data: EventInput) {
    setPending(true);
    try {
      const changes = event ? changedEventFields(data, event) : data;
      if (Object.keys(changes).length > 0) {
        await saveEvent(request, roleId, changes, event?.id);
        onChanged();
      }
      onClose();
    } finally {
      // EventForm displays save errors and keeps the current draft.
      setPending(false);
    }
  }

  async function remove() {
    if (editor.mode !== "delete" || pending) return;
    setPending(true);
    setDeleteError(null);
    try {
      await deleteEvent(request, editor.event.id);
      onChanged();
      onClose();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <FormDialog
      open
      pending={pending}
      onClose={onClose}
      title={titles[editor.mode]}
      description={editor.mode === "delete"
        ? `Delete “${editor.event.title}” and its status history?`
        : roleTitle}
      finalFocus={restoreFocus}
    >
      {editor.mode === "delete" ? (
        <FormActions error={deleteError}>
          <Button variant="outline" disabled={pending} onClick={onClose}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={pending} onClick={() => void remove()}>
            {pending ? "Deleting…" : "Delete event"}
          </Button>
        </FormActions>
      ) : (
        <EventForm event={event} pending={pending} onSave={save} onCancel={onClose} />
      )}
    </FormDialog>
  );
}
