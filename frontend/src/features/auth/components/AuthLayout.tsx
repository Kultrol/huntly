import { Target } from "lucide-react";
import type { ReactNode } from "react";
import { Link, Outlet } from "react-router";
import { AuthDotWave } from "./AuthDotWave";

/** Shares the welcome/auth shell; nested routes supply the form by default. */
export function AuthLayout({ children, aside }: { children?: ReactNode; aside?: ReactNode }) {
  return (
    <main className="grid min-h-svh lg:grid-cols-2">
      <div className="flex min-w-0 flex-col gap-6 px-6 py-6 sm:px-10 sm:py-8">
        <header className="flex">
          <Link
            to="/"
            aria-label="Huntly home"
            className="inline-flex items-center gap-2.5 rounded-lg text-lg font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
          >
            <span className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Target aria-hidden="true" className="size-5" />
            </span>
            Huntly
          </Link>
        </header>
        <div className="flex flex-1 items-center justify-center py-6 lg:pb-10">
          <div className="w-full max-w-sm">
            {children ?? <Outlet />}
          </div>
        </div>
      </div>
      <div className="relative isolate hidden flex-col justify-end overflow-hidden bg-accent lg:flex">
        <AuthDotWave />
        <div className="relative bg-linear-to-t from-accent from-40% to-transparent px-8 pt-16 pb-9 xl:px-12 xl:pb-12">
          {aside ?? (
            <>
              <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
                Your job search
              </p>
              <p className="mt-3 max-w-md text-3xl leading-tight font-semibold tracking-tight text-foreground xl:text-4xl">
                Applications, interviews, and follow-ups
              </p>
              <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
                Keep track of where you applied and what comes next.
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
