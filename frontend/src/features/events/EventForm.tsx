import { useState, type FormEvent } from "react";
import { getErrorMessage } from "@/api/client";
import { ChoiceField } from "@/components/ChoiceField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field } from "@/components/forms/Field";
import { FormActions } from "@/components/forms/FormActions";
import { readEventForm } from "./formValues";
import { eventStatuses, eventTypes, type EventInput, type RoleEvent } from "./types";

type EventFormProps = {
  event?: RoleEvent;
  pending: boolean;
  onSave: (data: EventInput) => Promise<void>;
  onCancel: () => void;
};

export function EventForm({ event, pending, onSave, onCancel }: EventFormProps) {
  const [eventType, setEventType] = useState<string>(event?.event_type ?? "");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(submission: FormEvent<HTMLFormElement>) {
    submission.preventDefault();
    if (pending) return;
    setError(null);
    try {
      await onSave(readEventForm(submission.currentTarget));
    } catch (error) {
      setError(getErrorMessage(error));
    }
  }

  return (
    <form onSubmit={handleSubmit} className="dialog-form" aria-busy={pending}>
      <div className="form-body">
        <fieldset disabled={pending} className="grid min-w-0 gap-4 @lg/form:grid-cols-2">
          <Field label="Event title (required)" className="@lg/form:col-span-2">
            {(control) => <Input {...control} name="title" required defaultValue={event?.title} />}
          </Field>
          <ChoiceField
            name="event_type"
            label="Event type (required)"
            required
            options={eventTypes}
            value={eventType}
            onValueChange={setEventType}
            placeholder="Choose a type"
          />
          <ChoiceField
            name="status"
            label="Status (required)"
            required
            options={eventStatuses}
            defaultValue={event?.status}
            placeholder="Choose a status"
          />
          {eventType === "custom" && (
            <Field label="Custom type (required)" className="@lg/form:col-span-2">
              {(control) => <Input {...control} name="custom_type_name" required defaultValue={event?.custom_type_name ?? ""} />}
            </Field>
          )}
          <Field label="Date (required)">
            {(control) => <Input {...control} name="event_date" type="date" required defaultValue={event?.event_date} />}
          </Field>
          <Field label="Time">
            {(control) => <Input {...control} name="event_time" type="time" step="1" defaultValue={event?.event_time ?? ""} />}
          </Field>
          <Field label="Location">
            {(control) => <Input {...control} name="location" defaultValue={event?.location ?? ""} />}
          </Field>
          <Field label="Link">
            {(control) => <Input {...control} name="url" type="url" defaultValue={event?.url ?? ""} />}
          </Field>
          <Field label="Notes" className="@lg/form:col-span-2">
            {(control) => <Textarea {...control} name="notes" rows={3} defaultValue={event?.notes ?? ""} />}
          </Field>
        </fieldset>
      </div>
      <FormActions error={error}>
        <Button type="button" variant="outline" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : event ? "Save event" : "Add event"}
        </Button>
      </FormActions>
    </form>
  );
}
