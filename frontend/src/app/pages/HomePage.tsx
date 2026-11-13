import { ArrowRight, CircleAlert, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { Link } from "react-router";
import { Button, buttonVariants } from "@/components/ui/button";
import { AuthLayout } from "@/features/auth/components/AuthLayout";
import { useHomeStartup } from "../useHomeStartup";

export default function HomePage() {
  const { status, isSlow, retry } = useHomeStartup();

  useEffect(() => {
    const previousTitle = document.title;
    document.title = "Welcome | Huntly";
    return () => {
      document.title = previousTitle;
    };
  }, []);

  return (
    <AuthLayout
      aside={
        <>
          <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
            Huntly preview
          </p>
          <p className="mt-3 max-w-md text-3xl leading-tight font-semibold tracking-tight text-foreground xl:text-4xl">
            Still in active development.
          </p>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
            We’re building a place to keep your job search organized. Features and
            screens will evolve as Huntly grows.
          </p>
        </>
      }
    >
      <div className="space-y-7">
        {/* Keep the live region mounted so changes are announced without moving keyboard focus. */}
        <div role="status" aria-live="polite" aria-atomic="true" className="space-y-4">
          {status !== "ready" && (
            <span className="grid size-12 place-items-center rounded-xl border border-primary/15 bg-accent text-primary">
              {status === "loading" ? (
                <LoaderCircle aria-hidden="true" className="size-6 motion-safe:animate-spin" />
              ) : (
                <CircleAlert aria-hidden="true" className="size-6" />
              )}
            </span>
          )}
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              {status === "ready"
                ? "Welcome to Huntly"
                : status === "error"
                  ? "We couldn’t connect"
                  : "Getting Huntly ready"}
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {status === "ready"
                ? "Sign in or create an account to get started."
                : status === "error"
                  ? "The server is taking longer than expected or your connection is unavailable. Try again in a moment."
                  : isSlow
                    ? "This is taking a little longer. We’re still trying to connect — no need to refresh."
                    : "Connecting to your workspace. This page will update automatically."}
            </p>
          </div>
        </div>

        {status === "loading" && (
          <section aria-labelledby="startup-explanation" className="space-y-2 rounded-xl border bg-card p-5">
            <h2 id="startup-explanation" className="text-sm font-semibold">Why the wait?</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Huntly’s server rests when it’s inactive to keep hosting costs down.
              If it’s waking up, the first visit can take about a minute. Thanks for your patience.
            </p>
          </section>
        )}

        {status === "error" && (
          <Button onClick={retry} className="h-11 w-full">
            <RefreshCw aria-hidden="true" />
            Try again
          </Button>
        )}

        {status === "ready" && (
          <nav aria-label="Get started" className="grid gap-3">
            <Link to="/login" className={buttonVariants({ className: "h-11 w-full" })}>
              Sign in
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
            <Link to="/register" className={buttonVariants({ variant: "outline", className: "h-11 w-full" })}>
              Create an account
            </Link>
          </nav>
        )}

        <p className="border-t pt-5 text-center text-xs leading-relaxed text-muted-foreground">
          Huntly is still in active development.<br />
          Thanks for being here while we build.
        </p>
      </div>
    </AuthLayout>
  );
}
