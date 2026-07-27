import { Navigate, useLocation } from "react-router-dom";

/** Redirect while preserving `?query` and `#hash` (legacy route aliases). */
export function RedirectPreserveSearch({ to }: { to: string }) {
  const location = useLocation();
  return <Navigate to={`${to}${location.search}${location.hash}`} replace />;
}
