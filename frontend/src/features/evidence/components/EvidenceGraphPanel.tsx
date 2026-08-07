import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Focus,
  Loader2,
  Network,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { layoutKnowledgeGraph } from "@/features/papers/mappers/graphLayout";
import type { GraphEdgeView, GraphNodeView } from "@/features/papers/mappers/graph";
import { evidenceApi } from "../api";
import type { ProjectGraphEdge, ProjectGraphNode } from "../types";
import { cn } from "@/lib/utils";

type NodeType = "paper" | "evidence" | "theme";
type TypeFilter = Record<NodeType, boolean>;

const DEFAULT_FILTER: TypeFilter = {
  paper: true,
  evidence: true,
  theme: true,
};

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

function typeLabel(type: string): string {
  if (type === "paper") return "Paper";
  if (type === "theme") return "Theme";
  return "Evidence";
}

function refFileId(node: ProjectGraphNode): number | null {
  const v = node.ref?.file_id;
  return typeof v === "number" ? v : typeof v === "string" ? Number(v) || null : null;
}

function refEvidenceId(node: ProjectGraphNode): number | null {
  const v = node.ref?.evidence_id;
  return typeof v === "number" ? v : typeof v === "string" ? Number(v) || null : null;
}

function GraphInspector({
  node,
  edges,
  nodesById,
  onClear,
  onFocusNeighbor,
}: {
  node: ProjectGraphNode;
  edges: ProjectGraphEdge[];
  nodesById: Map<string, ProjectGraphNode>;
  onClear: () => void;
  onFocusNeighbor: (id: string) => void;
}) {
  const navigate = useNavigate();
  const connected = edges.filter((e) => e.source === node.id || e.target === node.id);
  const fileId = refFileId(node);
  const evidenceId = refEvidenceId(node);

  return (
    <aside
      className="rounded-lg border border-border bg-card px-3 py-3"
      aria-label={`Selected ${typeLabel(node.type)}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {typeLabel(node.type)}
          </p>
          <h3 className="mt-0.5 text-[14px] font-semibold leading-snug text-foreground">
            {node.label}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="shrink-0 text-[11px] text-muted-foreground hover:text-foreground"
        >
          Clear
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {fileId != null ? (
          <Link
            to={`/papers/${fileId}`}
            className="rounded-md border border-border px-2 py-1 text-[12px] font-medium text-foreground hover:bg-muted/50"
          >
            Open paper
          </Link>
        ) : null}
        {node.type === "theme" ? (
          <button
            type="button"
            onClick={() => navigate("/research/compare?tab=themes")}
            className="rounded-md border border-border px-2 py-1 text-[12px] font-medium text-foreground hover:bg-muted/50"
          >
            Open Themes
          </button>
        ) : null}
        {node.type === "evidence" && evidenceId != null ? (
          <button
            type="button"
            onClick={() => navigate("/research/compare?tab=extract")}
            className="rounded-md border border-border px-2 py-1 text-[12px] font-medium text-foreground hover:bg-muted/50"
          >
            Structured evidence
          </button>
        ) : null}
        {connected.some((e) => e.type === "contradicts") ? (
          <button
            type="button"
            onClick={() => navigate("/research/compare?tab=gaps")}
            className="rounded-md border border-rose-500/30 px-2 py-1 text-[12px] font-medium text-rose-700 hover:bg-rose-500/5 dark:text-rose-400"
          >
            Explore conflicts
          </button>
        ) : null}
      </div>

      {connected.length ? (
        <div className="mt-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Connected ({connected.length})
          </p>
          <ul className="mt-1.5 max-h-40 space-y-1 overflow-y-auto">
            {connected.slice(0, 24).map((e) => {
              const otherId = e.source === node.id ? e.target : e.source;
              const other = nodesById.get(otherId);
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => onFocusNeighbor(otherId)}
                    className="flex w-full items-start gap-2 rounded-md px-1.5 py-1 text-left hover:bg-muted/50"
                  >
                    <span className="shrink-0 text-[10px] uppercase text-muted-foreground">
                      {e.type}
                    </span>
                    <span className="min-w-0 text-[12px] text-foreground/90">
                      {other?.label.slice(0, 80) || otherId}
                      {(other?.label.length ?? 0) > 80 ? "…" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <p className="mt-3 text-[12px] text-muted-foreground">No edges on this node.</p>
      )}
    </aside>
  );
}

/** RI-005 — interactive project graph (select · filter · pan/zoom · inspect). */
export function EvidenceGraphPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "graph", projectId],
    queryFn: () => evidenceApi.graph(projectId as number),
    enabled,
  });

  const [typeFilter, setTypeFilter] = useState<TypeFilter>(DEFAULT_FILTER);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hideEvidenceLabels, setHideEvidenceLabels] = useState(true);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const filtered = useMemo(() => {
    if (!q.data) return null;
    const nodes = q.data.nodes.filter((n) => typeFilter[n.type]);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = q.data.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { nodes, edges };
  }, [q.data, typeFilter]);

  const layout = useMemo(() => {
    if (!filtered) return null;
    return layoutKnowledgeGraph(toLayoutNodes(filtered.nodes), filtered.edges.map(
      (e): GraphEdgeView => ({
        id: e.id,
        key: e.id,
        source: e.source,
        target: e.target,
        relationship: e.type,
        confidence: undefined,
        metadata: {},
        evidenceCount: 0,
      }),
    ), { width: 720, height: 420 });
  }, [filtered]);

  const nodesById = useMemo(() => {
    const m = new Map<string, ProjectGraphNode>();
    for (const n of q.data?.nodes ?? []) m.set(n.id, n);
    return m;
  }, [q.data]);

  const highlightIds = useMemo(() => {
    const set = new Set<string>();
    if (!selectedId || !filtered) return set;
    set.add(selectedId);
    for (const e of filtered.edges) {
      if (e.source === selectedId || e.target === selectedId) {
        set.add(e.source);
        set.add(e.target);
      }
    }
    return set;
  }, [selectedId, filtered]);

  const selectedNode = selectedId ? nodesById.get(selectedId) ?? null : null;

  function focusNode(id: string) {
    setSelectedId(id);
    const p = layout?.positions[id];
    const svg = svgRef.current;
    if (!p || !svg) return;
    const rect = svg.getBoundingClientRect();
    setPan({
      x: rect.width / 2 - p.x * zoom,
      y: rect.height / 2 - p.y * zoom,
    });
  }

  if (!enabled) {
    return (
      <EmptyState
        icon={<Network className="size-7" />}
        title="Select a project"
        description="Open a project to explore how papers, evidence, and themes connect."
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

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest("[data-graph-node]")) return;
    dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    setPan({
      x: dragRef.current.panX + (e.clientX - dragRef.current.x),
      y: dragRef.current.panY + (e.clientY - dragRef.current.y),
    });
  };
  const onPointerUp = () => {
    dragRef.current = null;
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.metrics.paper_count} papers · {data.metrics.evidence_count} evidence ·{" "}
          {data.metrics.theme_count} themes · {data.metrics.edge_count} links
          {data.metrics.contradicts_count
            ? ` · ${data.metrics.contradicts_count} contradictions`
            : ""}
        </p>
        <div className="flex flex-wrap items-center gap-1">
          {(
            [
              ["paper", "Papers"],
              ["theme", "Themes"],
              ["evidence", "Evidence"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() =>
                setTypeFilter((prev) => ({ ...prev, [key]: !prev[key] }))
              }
              className={cn(
                "rounded-md border px-2 py-1 text-[11px] font-medium",
                typeFilter[key]
                  ? "border-foreground/20 bg-muted text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setHideEvidenceLabels((v) => !v)}
            className="rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
          >
            {hideEvidenceLabels ? "Show evidence labels" : "Hide evidence labels"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted/40"
          onClick={() => setZoom((z) => Math.min(2.5, z * 1.2))}
        >
          <ZoomIn className="size-3.5" /> Zoom in
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted/40"
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.2))}
        >
          <ZoomOut className="size-3.5" /> Zoom out
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted/40"
          onClick={() => {
            setPan({ x: 0, y: 0 });
            setZoom(1);
          }}
        >
          <Focus className="size-3.5" /> Fit
        </button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div
          className="relative h-[min(26rem,58vh)] overflow-hidden rounded-lg border border-border bg-muted/15"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        >
          <svg
            ref={svgRef}
            role="img"
            aria-label="Project evidence knowledge graph"
            className="size-full touch-none"
            onClick={() => setSelectedId(null)}
          >
            <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
              {(filtered?.edges ?? []).map((e) => {
                const a = layout?.positions[e.source];
                const b = layout?.positions[e.target];
                if (!a || !b) return null;
                const active =
                  selectedId != null &&
                  (e.source === selectedId || e.target === selectedId);
                const dimmed = selectedId != null && !active;
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
                      active && "stroke-foreground",
                      dimmed && "opacity-20",
                    )}
                    strokeWidth={active || e.type === "contradicts" ? 1.75 : 1}
                  />
                );
              })}
              {(filtered?.nodes ?? []).map((n) => {
                const p = layout?.positions[n.id];
                if (!p) return null;
                const selected = selectedId === n.id;
                const related = highlightIds.has(n.id);
                const dimmed = selectedId != null && !related;
                const r = n.type === "paper" ? 10 : n.type === "theme" ? 9 : 6;
                const showLabel =
                  n.type !== "evidence" || !hideEvidenceLabels || selected || related;
                return (
                  <g
                    key={n.id}
                    data-graph-node={n.id}
                    transform={`translate(${p.x} ${p.y})`}
                    tabIndex={0}
                    role="button"
                    aria-label={`${typeLabel(n.type)}: ${n.label}`}
                    aria-pressed={selected}
                    className="outline-none focus-visible:[&_circle]:stroke-[3]"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      setSelectedId(n.id);
                    }}
                    onKeyDown={(ev) => {
                      if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        setSelectedId(n.id);
                      }
                    }}
                  >
                    <circle
                      r={selected ? r + 2 : r}
                      fill="var(--color-card, #fff)"
                      stroke={strokeFor(n.type)}
                      strokeWidth={selected ? 2.5 : 1.5}
                      className={cn("cursor-pointer", dimmed && "opacity-25")}
                    />
                    {showLabel ? (
                      <text
                        y={r + 12}
                        textAnchor="middle"
                        className={cn(
                          "fill-muted-foreground",
                          dimmed && "opacity-25",
                          selected && "fill-foreground font-medium",
                        )}
                        style={{ fontSize: 9 }}
                      >
                        {n.label.slice(0, 28)}
                        {n.label.length > 28 ? "…" : ""}
                      </text>
                    ) : null}
                  </g>
                );
              })}
            </g>
          </svg>
          {!filtered?.nodes.length ? (
            <p className="pointer-events-none absolute inset-0 flex items-center justify-center text-[13px] text-muted-foreground">
              No nodes in the current filter.
            </p>
          ) : null}
        </div>

        {selectedNode ? (
          <GraphInspector
            node={selectedNode}
            edges={data.edges}
            nodesById={nodesById}
            onClear={() => setSelectedId(null)}
            onFocusNeighbor={focusNode}
          />
        ) : (
          <aside className="rounded-lg border border-dashed border-border bg-muted/20 px-3 py-3 text-[13px] text-muted-foreground">
            Click a node to inspect connections. Drag to pan · use filters to reduce clutter.
            <p className="mt-2 text-[11px]">
              Edges: paper→evidence · evidence→theme · conflict pairs (rose).
            </p>
          </aside>
        )}
      </div>
    </div>
  );
}
