import type { ReactNode } from "react";

type FormActionsProps = {
  error?: string | null;
  children: ReactNode;
};

export function FormActions({ error, children }: FormActionsProps) {
  return (
    <div className="form-actions space-y-3">
      {error && (
        <p role="alert" className="max-h-24 overflow-y-auto text-sm text-destructive wrap-anywhere">
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-end gap-2">{children}</div>
    </div>
  );
}
