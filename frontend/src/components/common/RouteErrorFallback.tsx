import { useRouteError, isRouteErrorResponse, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

/** D9 — React Router `errorElement` for unmatched render/loader failures. */
export function RouteErrorFallback() {
  const error = useRouteError();
  const navigate = useNavigate();

  let title = "Something went wrong";
  let detail = "This page couldn’t be loaded. Try again or return home.";

  if (isRouteErrorResponse(error)) {
    title = error.status === 404 ? "Page not found" : `Error ${error.status}`;
    detail =
      typeof error.data === "string"
        ? error.data
        : error.statusText || detail;
  } else if (error instanceof Error) {
    detail = error.message;
  }

  return (
    <div
      role="alert"
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center"
    >
      <div className="space-y-2">
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        <p className="max-w-md text-[13px] text-muted-foreground">{detail}</p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => window.location.reload()}>
          Reload
        </Button>
        <Button onClick={() => navigate("/")}>Go home</Button>
      </div>
    </div>
  );
}
