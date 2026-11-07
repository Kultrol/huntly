import { Link } from "react-router";
import { buttonVariants } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <main>
      <h1>Page Not Found</h1>
      <Link to="/" className={buttonVariants()}>Return to Home Page</Link>
    </main>
  );
}
