import { Field } from "@/components/forms/Field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type ChoiceFieldProps = {
  label: string;
  name?: string;
  options: Record<string, string>;
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  optionalLabel?: string;
  hint?: string;
  error?: string;
};

export function ChoiceField({
  label,
  name,
  options,
  defaultValue = "",
  value,
  onValueChange,
  placeholder = "Choose an option",
  required = false,
  optionalLabel = "Unassigned",
  hint,
  error,
}: ChoiceFieldProps) {
  return (
    <Field label={label} hint={hint} error={error}>
      {(control) => (
        <Select
          name={name}
          defaultValue={defaultValue}
          value={value}
          onValueChange={(next) => onValueChange?.(next ?? "")}
          required={required}
        >
          <SelectTrigger {...control} className="w-full bg-background">
            <SelectValue>
              {(selected: string | null) => options[selected ?? ""] ?? (required ? placeholder : optionalLabel)}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {!required && <SelectItem value="">{optionalLabel}</SelectItem>}
            {Object.entries(options).map(([key, text]) => (
              <SelectItem key={key} value={key}>{text}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </Field>
  );
}
