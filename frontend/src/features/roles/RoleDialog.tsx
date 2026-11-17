import { useState } from "react";
import { getErrorMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { FormDialog } from "@/components/forms/FormDialog";
import { FormActions } from "@/components/forms/FormActions";
import { RoleForm } from "./RoleForm";
import { RoleDetails } from "./RoleDetails";
import type { RoleChange, TrackedRole } from "./types";

export type RoleEditor = { mode: "create" } | { mode: "view" | "edit" | "delete"; role: TrackedRole };

type RoleDialogProps = {
  editor: RoleEditor;
  companyName?: string;
  onClose: () => void;
  onSave: (change: RoleChange) => Promise<TrackedRole>;
  onSaved: (role: TrackedRole) => void;
  onDelete: (id: string) => Promise<void>;
  restoreFocus: () => HTMLElement | null;
};

const titles = { view: "Role details", create: "Add role", edit: "Edit role", delete: "Delete role?" };

export function RoleDialog({
  editor, companyName, onClose, onSave, onSaved, onDelete, restoreFocus,
}: RoleDialogProps) {
  const [pending, setPending] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<"view" | "edit" | "delete">("view");
  const mode = editor.mode === "view" ? previewMode : editor.mode;
  const role = editor.mode === "create" ? undefined : editor.role;
  const description = editor.mode === "create"
    ? "Track an opportunity and its events."
    : mode === "delete"
      ? `Deleting ${editor.role.title} also removes its linked events and status history.`
      : mode === "view" ? "Role details" : editor.role.title;

  function cancelAction() {
    if (editor.mode === "view") {
      setDeleteError(null);
      setPreviewMode("view");
    } else {
      onClose();
    }
  }

  async function save(change: RoleChange) {
    if ("id" in change && !Object.keys(change.data).length) {
      cancelAction();
      return;
    }
    setPending(true);
    try {
      const saved = await onSave(change);
      onSaved(saved);
      if (editor.mode === "view") setPreviewMode("view");
    } finally {
      // RoleForm displays save errors and keeps the current draft.
      setPending(false);
    }
  }

  async function remove() {
    if (!role || mode !== "delete" || pending) return;
    setPending(true);
    setDeleteError(null);
    try {
      await onDelete(role.id);
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
      wide
      onClose={onClose}
      pending={pending}
      finalFocus={restoreFocus}
      title={mode === "view" && role ? role.title : titles[mode]}
      description={description}
    >
      {mode === "view" && role ? (
        <div className="dialog-form">
          <div className="form-body">
            <RoleDetails role={role} companyName={companyName} />
          </div>
          <FormActions>
            <Button variant="ghost" onClick={() => setPreviewMode("delete")}>Delete role</Button>
            <Button autoFocus onClick={() => setPreviewMode("edit")}>Edit role</Button>
          </FormActions>
        </div>
      ) : mode === "delete" ? (
        <FormActions error={deleteError}>
          <Button autoFocus variant="outline" disabled={pending} onClick={cancelAction}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={pending} onClick={() => void remove()}>
            {pending ? "Deleting…" : "Delete role"}
          </Button>
        </FormActions>
      ) : (
        <RoleForm
          role={role}
          companyName={companyName}
          isSaving={pending}
          onSave={save}
          onCancel={cancelAction}
        />
      )}
    </FormDialog>
  );
}
