import { useState, type FormEvent } from "react";
import { getErrorMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field } from "@/components/forms/Field";
import { FormActions } from "@/components/forms/FormActions";
import { ChoiceField } from "@/components/ChoiceField";
import { UnavailableAction } from "@/components/feedback/UnavailableAction";
import { readRoleForm, roleFormValues } from "./formValues";
import { rolePriorities, roleStatuses, roleTypes, type RoleChange, type TrackedRole } from "./types";

type RoleFormProps = {
  role?: TrackedRole;
  companyName?: string;
  isSaving: boolean;
  onSave: (change: RoleChange) => Promise<void>;
  onCancel: () => void;
};

export function RoleForm({ role, companyName, isSaving, onSave, onCancel }: RoleFormProps) {
  const values = roleFormValues(role);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSaving) return;
    setError(null);
    try {
      await onSave(readRoleForm(event.currentTarget, role));
    } catch (error) {
      setError(getErrorMessage(error));
    }
  }

  return (
    <form className="dialog-form" onSubmit={handleSubmit} aria-busy={isSaving}>
      <div className="form-body">
        <fieldset className="grid min-w-0 gap-4 disabled:opacity-60 @lg/form:grid-cols-2" disabled={isSaving}>
          <Field label="Role title (required)" className="@lg/form:col-span-2">
            {(control) => <Input {...control} name="title" defaultValue={values.title} required autoFocus />}
          </Field>
          <ChoiceField
            label="Status (required)"
            name="status"
            defaultValue={values.status}
            required
            options={roleStatuses}
            placeholder="Choose a status"
          />
          <Field label="Company">
            {(control) => (
              <UnavailableAction
                message="Feature not implemented yet"
                render={
                  <Button
                    {...control}
                    variant="outline"
                    className="min-w-0 justify-start overflow-hidden font-normal text-muted-foreground"
                  />
                }
              >
                <span className="truncate">{companyName ?? "Select a company"}</span>
              </UnavailableAction>
            )}
          </Field>
          <ChoiceField label="Role type" name="role_type" defaultValue={values.role_type} options={roleTypes} />
          <ChoiceField label="Priority" name="priority" defaultValue={values.priority} options={rolePriorities} />
          <Field label="Location">
            {(control) => <Input {...control} name="location" defaultValue={values.location} />}
          </Field>
          <Field label="Application date">
            {(control) => <Input {...control} name="applied_at" type="date" defaultValue={values.applied_at} />}
          </Field>
          <Field label="Listing URL" className="@lg/form:col-span-2">
            {(control) => <Input {...control} name="listing_url" type="url" defaultValue={values.listing_url} />}
          </Field>
          <fieldset className="grid min-w-0 gap-3 rounded-lg border px-3 pb-3 @lg/form:col-span-2 @lg/form:grid-cols-[1fr_1fr_minmax(6rem,0.75fr)]">
            <legend className="px-1 font-medium">Annual salary</legend>
            <Field label="Minimum">
              {(control) => <Input {...control} name="salary_min" type="number" min="0" step="any" defaultValue={values.salary_min} />}
            </Field>
            <Field label="Maximum">
              {(control) => <Input {...control} name="salary_max" type="number" min="0" step="any" defaultValue={values.salary_max} />}
            </Field>
            <Field label="Currency">
              {(control) => <Input {...control} name="salary_currency" placeholder="e.g. USD" defaultValue={values.salary_currency} />}
            </Field>
          </fieldset>
          <Field label="Description" className="@lg/form:col-span-2">
            {(control) => <Textarea {...control} name="description" defaultValue={values.description} rows={3} />}
          </Field>
          <Field label="Notes" className="@lg/form:col-span-2">
            {(control) => <Textarea {...control} name="notes" defaultValue={values.notes} rows={3} />}
          </Field>
        </fieldset>
      </div>
      <FormActions error={error}>
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving…" : role ? "Save changes" : "Add role"}
        </Button>
      </FormActions>
    </form>
  );
}
