import { CircleAlert, LoaderCircle } from "lucide-react";
import { useEffect, useId, useRef, type ComponentProps, type ReactNode, type SubmitEvent } from "react";
import { Link, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type AuthFormProps = {
  title: string;
  pageTitle: string;
  description: string;
  error: string | null;
  isPending: boolean;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
  submitLabel: string;
  alternate: { prompt: string; label: string; to: string };
  children: ReactNode;
};

/** Renders the shared form shell while each page supplies its fields and submit handler. */
export function AuthForm({
  title,
  pageTitle,
  description,
  error,
  isPending,
  onSubmit,
  submitLabel,
  alternate,
  children,
}: AuthFormProps) {
  // Carry the return destination when the user switches between login and registration.
  const { state } = useLocation();
  const titleId = useId();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = pageTitle;
    // Give assistive technology the new route heading when the form opens.
    headingRef.current?.focus();
    return () => {
      document.title = previousTitle;
    };
  }, [pageTitle]);

  return (
    <div className="space-y-7">
      <div className="space-y-2">
        <h1 ref={headingRef} id={titleId} tabIndex={-1} className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {title}
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
      {/* The submit handler shows validation feedback inline. */}
      <form noValidate onSubmit={onSubmit} aria-labelledby={titleId} aria-busy={isPending} className="grid gap-5">
        {error && (
          <p role="alert" className="flex items-start gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span>{error}</span>
          </p>
        )}
        {children}
        <Button type="submit" disabled={isPending} className="h-11 w-full">
          {isPending && <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />}
          {submitLabel}
        </Button>
      </form>
      <p className="border-t border-border pt-5 text-center text-sm text-muted-foreground">
        {alternate.prompt}{" "}
        <Link
          to={alternate.to}
          state={state}
          className="rounded-sm font-semibold text-primary underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
        >
          {alternate.label}
        </Link>
      </p>
    </div>
  );
}

type AuthFieldProps = Omit<ComponentProps<typeof Input>, "id" | "className"> & {
  label: string;
  hint?: string;
  error?: string;
};

/** Associates the current hint or error with the input for assistive technology. */
export function AuthField({ label, hint, error, ...input }: AuthFieldProps) {
  const id = useId();
  const message = error ?? hint;
  const messageId = message ? `${id}-message` : undefined;

  return (
    <div data-invalid={error ? true : undefined} className="group/field grid gap-2">
      <label htmlFor={id} className="text-sm leading-none font-medium group-data-invalid/field:text-destructive">
        {label}
      </label>
      <Input
        {...input}
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={messageId}
        className="h-11 bg-card px-3 dark:bg-card"
      />
      {message && (
        <p
          id={messageId}
          role={error ? "alert" : undefined}
          className={cn("text-xs", error ? "text-destructive" : "text-muted-foreground")}
        >
          {message}
        </p>
      )}
    </div>
  );
}
