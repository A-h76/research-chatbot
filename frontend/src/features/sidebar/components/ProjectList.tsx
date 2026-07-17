import { useNavigate } from "react-router-dom";
import { Settings2 } from "lucide-react";
import { useProjects } from "@/features/projects/useProjects";
import { useUI } from "@/context/UIContext";
import { cn } from "@/lib/utils";

export function ProjectList() {
  const { data: projects = [] } = useProjects();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const navigate = useNavigate();

  if (!projects.length) return null;

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between px-3 pb-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Projects</span>
        <button
          className="rounded-md p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title="Manage projects"
          onClick={() => navigate("/projects")}
        >
          <Settings2 className="size-3.5" />
        </button>
      </div>
      <div className="flex flex-col gap-0.5 px-2">
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => setCurrentProjectId(currentProjectId === p.id ? null : p.id)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm text-sidebar-foreground hover:bg-sidebar-accent",
              currentProjectId === p.id && "bg-sidebar-accent font-medium"
            )}
          >
            <span>{p.emoji}</span>
            <span className="min-w-0 flex-1 truncate">{p.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
