import { useEffect } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { useUI } from "@/context/UIContext";

/** Deep link: /projects/:projectId/writing → /writing with project locked in UIContext. */
export function ProjectWritingRedirect() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const { setCurrentProjectId } = useUI();

  useEffect(() => {
    const id = Number(projectId);
    if (Number.isFinite(id) && id > 0) setCurrentProjectId(id);
  }, [projectId, setCurrentProjectId]);

  const qs = searchParams.toString();
  return <Navigate to={qs ? `/writing?${qs}` : "/writing"} replace />;
}
