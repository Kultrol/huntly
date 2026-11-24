import { useState } from "react";
import { getErrorMessage } from "@/api/client";
import { FormActions } from "@/components/forms/FormActions";
import { FormDialog } from "@/components/forms/FormDialog";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/session/useAuth";
import { CompanyForm } from "./CompanyForm";
import { deleteCompany, saveCompany, type Company, type CompanyFields } from "./api";

export type CompanyEditor = { mode: "create" } | { mode: "view" | "edit" | "delete"; company: Company };

type Props = {
  editor: CompanyEditor;
  onClose: () => void;
  onSaved: (company: Company) => void;
  onDeleted?: () => void;
  restoreFocus: () => HTMLElement | null;
};

export function CompanyDialog({ editor, onClose, onSaved, onDeleted, restoreFocus }: Props) {
  const { user, request } = useAuth();
  const [action, setAction] = useState<"view" | "edit" | "delete">("view");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const company = editor.mode === "create" ? undefined : editor.company;
  const mode = editor.mode === "view" ? action : editor.mode;
  const title = {
    create: "Add company",
    edit: "Edit company",
    delete: "Delete company?",
    view: company?.name ?? "",
  }[mode];
  const description = {
    create: "Start with the company name.",
    view: "Company details",
    edit: company?.name ?? "",
    delete: `Roles and contacts linked to ${company?.name} will be kept with their company cleared.`,
  }[mode];

  function cancel() {
    setError("");
    if (editor.mode === "view") setAction("view");
    else onClose();
  }

  async function save(fields: CompanyFields) {
    if (!user) return;
    setPending(true);
    try {
      onSaved(await saveCompany(request, user.id, fields, company));
      setAction("view");
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (!company || pending) return;
    setPending(true);
    setError("");
    try {
      await deleteCompany(request, company.id);
      onDeleted?.();
      onClose();
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <FormDialog
      open
      title={title}
      description={description}
      pending={pending}
      finalFocus={restoreFocus}
      onClose={onClose}
    >
      {mode === "create" || mode === "edit" ? (
        <CompanyForm company={company} onSave={save} pending={pending} onCancel={cancel} />
      ) : mode === "delete" ? (
        <FormActions error={error}>
          <Button variant="outline" autoFocus disabled={pending} onClick={cancel}>Cancel</Button>
          <Button variant="destructive" disabled={pending} onClick={remove}>{pending ? "Deleting…" : "Delete company"}</Button>
        </FormActions>
      ) : company && (
        <div className="dialog-form">
          <dl className="form-body grid gap-4 text-sm">
            <div><dt className="font-medium">Location</dt><dd className="wrap-anywhere">{company.location || "—"}</dd></div>
            {([["Website", company.website], ["LinkedIn", company.linkedin_url]] as const).map(([label, url]) => (
              <div key={label}>
                <dt className="font-medium">{label}</dt>
                <dd>{url ? <a className="text-primary underline wrap-anywhere" href={url} target="_blank" rel="noreferrer">{url}</a> : "—"}</dd>
              </div>
            ))}
            <div><dt className="font-medium">Notes</dt><dd className="whitespace-pre-wrap wrap-anywhere">{company.notes || "—"}</dd></div>
          </dl>
          <FormActions>
            <Button variant="ghost" onClick={() => setAction("delete")}>Delete company</Button>
            <Button autoFocus onClick={() => setAction("edit")}>Edit company</Button>
          </FormActions>
        </div>
      )}
    </FormDialog>
  );
}
