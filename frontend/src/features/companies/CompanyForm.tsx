import { useState, type FormEvent } from "react";
import { ApiError, getErrorMessage } from "@/api/client";
import { Field } from "@/components/forms/Field";
import { FormActions } from "@/components/forms/FormActions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { Company, CompanyFields } from "./api";

type Props = {
  company?: Company;
  pending: boolean;
  onSave: (fields: CompanyFields) => Promise<void>;
  onCancel: () => void;
};

export function CompanyForm({ company, pending, onSave, onCancel }: Props) {
  const [error, setError] = useState("");
  const [nameError, setNameError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // The dialog is portalled, but React still bubbles submit to the role form that opened it.
    event.stopPropagation();
    if (pending) return;
    const data = new FormData(event.currentTarget);
    const text = (key: keyof CompanyFields) => String(data.get(key) ?? "").trim();
    const name = text("name");
    if (!name) {
      setNameError("Enter a company name.");
      return;
    }
    setNameError("");
    setError("");
    try {
      await onSave({
        name,
        website: text("website") || null,
        linkedin_url: text("linkedin_url") || null,
        location: text("location") || null,
        notes: text("notes") || null,
      });
    } catch (cause) {
      // The company API returns 400 for a duplicate normalized name on create or edit.
      if (cause instanceof ApiError && cause.status === 400) setNameError("You already have a company with this name.");
      else setError(getErrorMessage(cause));
    }
  }

  return (
    <form className="dialog-form" onSubmit={submit}>
      <div className="form-body">
        <fieldset disabled={pending} className="grid min-w-0 gap-4 @lg/form:grid-cols-2">
          <Field label="Company name (required)" error={nameError}>
            {(control) => <Input {...control} name="name" defaultValue={company?.name} onChange={() => setNameError("")} maxLength={255} required autoFocus />}
          </Field>
          <Field label="Location">
            {(control) => <Input {...control} name="location" defaultValue={company?.location ?? ""} maxLength={255} />}
          </Field>
          <Field label="Website">
            {(control) => <Input {...control} name="website" type="url" pattern="https?://.+" title="Enter an http:// or https:// URL" defaultValue={company?.website ?? ""} maxLength={255} />}
          </Field>
          <Field label="LinkedIn URL">
            {(control) => <Input {...control} name="linkedin_url" type="url" pattern="https?://.+" title="Enter an http:// or https:// URL" defaultValue={company?.linkedin_url ?? ""} maxLength={255} />}
          </Field>
          <Field label="Notes" className="@lg/form:col-span-2">
            {(control) => <Textarea {...control} name="notes" defaultValue={company?.notes ?? ""} rows={3} />}
          </Field>
        </fieldset>
      </div>
      <FormActions error={error}>
        <Button type="button" variant="outline" disabled={pending} onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={pending}>{pending ? "Saving…" : company ? "Save changes" : "Add company"}</Button>
      </FormActions>
    </form>
  );
}
