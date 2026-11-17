import { LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LoadingState({ message }: { message: string }) {
  return (
    <p role="status" className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
      <LoaderCircle aria-hidden="true" className="size-4 shrink-0 motion-safe:animate-spin" />
      {message}
    </p>
  );
}

type LoadErrorProps = {
  message: string;
  onRetry: () => void;
  retryLabel?: string;
};

export function LoadError({ message, onRetry, retryLabel = "Retry" }: LoadErrorProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/30 p-4">
      <p role="alert" className="min-w-0 text-sm text-destructive wrap-anywhere">{message}</p>
      <Button variant="outline" onClick={onRetry}>{retryLabel}</Button>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground wrap-anywhere">
      {message}
    </p>
  );
}
