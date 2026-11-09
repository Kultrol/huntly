import { FileQuestionMark } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { buttonVariants } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

const pageTitle = "Page not found | Huntly";

export default function NotFoundPage() {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = pageTitle;
    headingRef.current?.focus();
    return () => {
      document.title = previousTitle;
    };
  }, []);

  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <FileQuestionMark aria-hidden="true" />
          </EmptyMedia>
          <EmptyTitle>
            <h1
              ref={headingRef}
              tabIndex={-1}
              className="outline-none"
            >
              Page Not Found
            </h1>
          </EmptyTitle>
          <EmptyDescription>This address does not match a page.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Link to="/" className={buttonVariants()}>
            Return to Home Page
          </Link>
        </EmptyContent>
      </Empty>
    </main>
  );
}
