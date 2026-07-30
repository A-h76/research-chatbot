import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Network } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { layoutKnowledgeGraph } from "@/features/papers/mappers/graphLayout";
import type { GraphEdgeView, GraphNodeView } from "@/features/papers/mappers/graph";
import { evidenceApi } from "../api";
import type { ProjectGraphNode } from "../types";
import { cn } from "@/lib/utils";

function toLayoutNodes(nodes: ProjectGraphNode[]): GraphNodeView[] {
  return nodes.map((n) => ({
    id: n.id,
    key: n.id,
    label: n.label,
    type: n.type,
    category:
      n.type === "paper" ? "study" : n.type === "theme" ? "clinical" : ("evidence" as const),
    confidence: undefined,
    metadata: {},
    evidenceCount: 0,
    properties: {},
  }));
}

function strokeFor(type: string): string {
  if (type === "paper") return "var(--color-muted-foreground, #666)";
  if (type === "theme") return "var(--color-primary, #111)";
  return "var(--sem-ready, #1a7f4e)";
}

/** RI-005 — project graph over papers / evidence / themes. */
export function EvidenceGraphPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "graph", projectId],
    queryFn: () => evidenceApi.graph(projectId as number),
    enabled,
  });

  const layout = useMemo(() => {
    if (!q.data) return null;
    const nodes = toLayoutNodes(q.data.nodes);
    const edges: GraphEdgeView[] = q.data.edges.map((e) => ({
      id: e.id,
      key: e.id,
      source: e.source,
      target: e.target,
      relationship: e.type,
      confidence: undefined,
      metadata: {},
      evidenceCount: 0,
    }));
    return layoutKnowledgeGraph(nodes, edges, { width: 720, height: 420 });
  }, [q.data]);

  if (!enabled) {
    return (
      <EmptyState
        icon={<Network className="size-7" />}
        title="Select a project"
        description="Open a project to view the evidence knowledge graph."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Building graph…
        </div>
        <Skeleton className="h-64 rounded-lg" />
      </div>
    );
  }

  if (q.isError || !q.data) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load project graph. Extract evidence first.
      </p>
    );
  }

  const data = q.data;
  if (!data.nodes.length) {
    return (
      <EmptyState
        icon={<Network className="size-7" />}
        title="Empty graph"
        description="Add papers and extract evidence to connect papers → evidence → themes."
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-muted-foreground">
        {data.metrics.paper_count} papers · {data.metrics.evidence_count} evidence ·{" "}
        {data.metrics.theme_count} themes · {data.metrics.edge_count} links
        {data.metrics.contradicts_count
          ? ` · ${data.metrics.contradicts_count} contradictions`
          : ""}
      </p>
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <svg
          viewBox={`0 0 ${layout?.width ?? 720} ${layout?.height ?? 420}`}
          className="h-[22rem] w-full"
          role="img"
          aria-label="Project evidence knowledge graph"
        >
          {(data.edges || []).map((e) => {
            const a = layout?.positions[e.source];
            const b = layout?.positions[e.target];
            if (!a || !b) return null;
            return (
              <line
                key={e.id}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                className={cn(
                  "stroke-border",
                  e.type === "contradicts" && "stroke-rose-500/70",
                  e.type === "in_theme" && "stroke-primary/40",
                )}
                strokeWidth={e.type === "contradicts" ? 1.5 : 1}
              />
            );
          })}
          {data.nodes.map((n) => {
            const p = layout?.positions[n.id];
            if (!p) return null;
            const r = n.type === "paper" ? 10 : n.type === "theme" ? 9 : 6;
            return (
              <g key={n.id}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={r}
                  fill="var(--color-card, #fff)"
                  stroke={strokeFor(n.type)}
                  strokeWidth={1.5}
                />
                <title>{`${n.type}: ${n.label}`}</title>
                {(n.type === "paper" || n.type === "theme") && (
                  <text
                    x={p.x}
                    y={p.y + r + 12}
                    textAnchor="middle"
                    className="fill-muted-foreground"
                    style={{ fontSize: 9 }}
                  >
                    {n.label.slice(0, 28)}
                    {n.label.length > 28 ? "…" : ""}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <p className="text-[10px] text-muted-foreground">
        Edges: paper→evidence (from), evidence→theme (in_theme), conflict pairs (contradicts).
        Hash {(data.run.input_hash || "").slice(0, 10)}…
      </p>
    </div>
  );
}
