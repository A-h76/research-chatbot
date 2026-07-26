import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Focus, Network, Search, ZoomIn, ZoomOut } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import {
  filterKnowledgeGraph,
  formatConfidence,
  formatLabel,
  mapKnowledgeGraph,
  uniqueCategories,
  uniqueRelationships,
  type GraphCategory,
  type GraphEdgeView,
  type GraphNodeView,
  type KnowledgeGraphViewModel,
} from "../mappers/graph";
import { layoutKnowledgeGraph } from "../mappers/graphLayout";
import { resolveGraphNodeId } from "../mappers/chat";

type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function categoryStroke(category: GraphCategory): string {
  switch (category) {
    case "clinical":
      return "var(--color-foreground)";
    case "pico":
      return "var(--color-primary, #111)";
    case "evidence":
      return "var(--sem-ready, #1a7f4e)";
    case "study":
      return "var(--color-muted-foreground, #666)";
    default:
      return "var(--color-border, #ccc)";
  }
}

function SummaryStrip({ view }: { view: KnowledgeGraphViewModel }) {
  const cells: [string, string][] = [
    ["Nodes", String(view.summary.nodeCount)],
    ["Relationships", String(view.summary.edgeCount)],
  ];
  if (view.summary.connectedComponents != null) {
    cells.push(["Components", String(view.summary.connectedComponents)]);
  }
  if (view.summary.overallConfidence != null) {
    cells.push(["Confidence", formatConfidence(view.summary.overallConfidence) ?? "—"]);
  } else if (view.summary.averageConfidence != null) {
    cells.push(["Avg confidence", formatConfidence(view.summary.averageConfidence) ?? "—"]);
  }

  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="Graph summary">
      {cells.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-border bg-card px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
          <dd className="mt-0.5 text-sm font-medium tabular-nums text-foreground">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function GraphCanvas({
  nodes,
  edges,
  matchedNodeIds,
  selection,
  onSelect,
  focusNodeId,
}: {
  nodes: GraphNodeView[];
  edges: GraphEdgeView[];
  matchedNodeIds: Set<string>;
  selection: Selection;
  onSelect: (sel: Selection) => void;
  focusNodeId: string | null;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);

  const layout = useMemo(() => layoutKnowledgeGraph(nodes, edges), [nodes, edges]);

  useEffect(() => {
    if (!focusNodeId) return;
    const p = layout.positions[focusNodeId];
    if (!p) return;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setPan({
      x: rect.width / 2 - p.x * zoom,
      y: rect.height / 2 - p.y * zoom,
    });
  }, [focusNodeId, layout.positions, zoom]);

  const selectedNodeId = selection?.kind === "node" ? selection.id : null;
  const selectedEdgeId = selection?.kind === "edge" ? selection.id : null;
  const highlightIds = useMemo(() => {
    const set = new Set<string>();
    if (selectedNodeId) {
      set.add(selectedNodeId);
      for (const e of edges) {
        if (e.source === selectedNodeId || e.target === selectedNodeId) {
          set.add(e.source);
          set.add(e.target);
        }
      }
    }
    if (selectedEdgeId) {
      const e = edges.find((x) => x.id === selectedEdgeId);
      if (e) {
        set.add(e.source);
        set.add(e.target);
      }
    }
    return set;
  }, [selectedNodeId, selectedEdgeId, edges]);

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest("[data-graph-node],[data-graph-edge]")) return;
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

  const fit = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => setZoom((z) => Math.min(2.5, z * 1.2))}
          aria-label="Zoom in"
        >
          <ZoomIn className="size-3.5" aria-hidden /> Zoom in
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.2))}
          aria-label="Zoom out"
        >
          <ZoomOut className="size-3.5" aria-hidden /> Zoom out
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={fit}
          aria-label="Fit graph to screen"
        >
          <Focus className="size-3.5" aria-hidden /> Fit
        </button>
      </div>

      <div
        className="relative h-[min(28rem,60vh)] overflow-hidden rounded-xl border border-border bg-muted/20"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <svg
          ref={svgRef}
          role="img"
          aria-label="Knowledge graph canvas"
          className="size-full touch-none"
          onClick={() => onSelect(null)}
        >
          <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
            {edges.map((e) => {
              const s = layout.positions[e.source];
              const t = layout.positions[e.target];
              if (!s || !t) return null;
              const active =
                selectedEdgeId === e.id ||
                (selectedNodeId != null &&
                  (e.source === selectedNodeId || e.target === selectedNodeId));
              const dimmed = selection != null && !active;
              return (
                <g key={e.key} data-graph-edge={e.id}>
                  <line
                    x1={s.x}
                    y1={s.y}
                    x2={t.x}
                    y2={t.y}
                    stroke="currentColor"
                    strokeWidth={active ? 2.25 : 1.25}
                    strokeDasharray={e.inferred ? "4 3" : undefined}
                    className={cn(
                      "text-border",
                      active && "text-foreground",
                      dimmed && "opacity-20",
                    )}
                    tabIndex={0}
                    role="button"
                    aria-label={`Relationship ${formatLabel(e.relationship)}`}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onSelect({ kind: "edge", id: e.id });
                    }}
                    onKeyDown={(ev) => {
                      if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        onSelect({ kind: "edge", id: e.id });
                      }
                    }}
                  />
                </g>
              );
            })}

            {nodes.map((n) => {
              const p = layout.positions[n.id];
              if (!p) return null;
              const selected = selectedNodeId === n.id;
              const related = highlightIds.has(n.id);
              const matched = matchedNodeIds.has(n.id);
              const dimmed = selection != null && !related && !selected;
              const r = selected || matched ? 16 : 12;
              return (
                <g
                  key={n.key}
                  data-graph-node={n.id}
                  transform={`translate(${p.x} ${p.y})`}
                  tabIndex={0}
                  role="button"
                  aria-label={`${n.label}, ${formatLabel(n.type)}${
                    n.confidence != null ? `, confidence ${formatConfidence(n.confidence)}` : ""
                  }`}
                  aria-pressed={selected}
                  className="outline-none focus-visible:[&_circle]:stroke-[3]"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    onSelect({ kind: "node", id: n.id });
                  }}
                  onKeyDown={(ev) => {
                    if (ev.key === "Enter" || ev.key === " ") {
                      ev.preventDefault();
                      onSelect({ kind: "node", id: n.id });
                    }
                  }}
                >
                  <circle
                    r={r}
                    fill="var(--color-card, #fff)"
                    stroke={categoryStroke(n.category)}
                    strokeWidth={selected || matched ? 2.5 : 1.5}
                    className={cn(dimmed && "opacity-25")}
                  />
                  <text
                    y={r + 12}
                    textAnchor="middle"
                    className={cn(
                      "fill-foreground text-[10px]",
                      dimmed && "opacity-25",
                      matched && "font-semibold",
                    )}
                  >
                    {n.label.length > 22 ? `${n.label.slice(0, 20)}…` : n.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
        {nodes.length === 0 && (
          <p className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            No nodes in the current filter.
          </p>
        )}
      </div>
    </div>
  );
}

function DetailPanel({
  view,
  selection,
  onClear,
}: {
  view: KnowledgeGraphViewModel;
  selection: Selection;
  onClear: () => void;
}) {
  if (!selection) {
    return (
      <aside
        aria-label="Selection details"
        className="rounded-xl border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground"
      >
        Select a node or relationship to inspect details.
      </aside>
    );
  }

  if (selection.kind === "node") {
    const node = view.nodes.find((n) => n.id === selection.id);
    if (!node) return null;
    const connected = view.edges.filter((e) => e.source === node.id || e.target === node.id);
    const byId = new Map(view.nodes.map((n) => [n.id, n]));

    return (
      <aside
        aria-label={`Node details for ${node.label}`}
        className="rounded-xl border border-border bg-card p-4 space-y-3"
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-medium text-foreground">{node.label}</h3>
            <p className="text-xs text-muted-foreground">
              {formatLabel(node.type)} · {formatLabel(node.category)}
            </p>
          </div>
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            onClick={onClear}
          >
            Clear
          </button>
        </div>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between gap-2">
            <dt className="text-muted-foreground">Confidence</dt>
            <dd className="tabular-nums">{formatConfidence(node.confidence) ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-muted-foreground">Evidence refs</dt>
            <dd className="tabular-nums">{node.evidenceCount}</dd>
          </div>
        </dl>
        {Object.keys(node.properties).length > 0 && (
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Metadata</p>
            <dl className="space-y-1 text-xs">
              {Object.entries(node.properties).map(([k, v]) => (
                <div key={k} className="grid grid-cols-[7rem_1fr] gap-2">
                  <dt className="text-muted-foreground">{formatLabel(k)}</dt>
                  <dd className="break-words text-foreground">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        {connected.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Relationships</p>
            <ul className="space-y-1 text-xs" role="list">
              {connected.map((e) => {
                const otherId = e.source === node.id ? e.target : e.source;
                const other = byId.get(otherId);
                return (
                  <li key={e.key} className="rounded-md border border-border px-2 py-1.5">
                    <span className="font-medium">{formatLabel(e.relationship)}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      → {other?.label ?? otherId}
                      {e.inferred ? " (inferred)" : ""}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </aside>
    );
  }

  const edge = view.edges.find((e) => e.id === selection.id);
  if (!edge) return null;
  const source = view.nodes.find((n) => n.id === edge.source);
  const target = view.nodes.find((n) => n.id === edge.target);

  return (
    <aside
      aria-label={`Relationship ${edge.relationship}`}
      className="rounded-xl border border-border bg-card p-4 space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-medium text-foreground">
            {formatLabel(edge.relationship)}
          </h3>
          {edge.inferred && <p className="text-xs text-muted-foreground">Inferred relationship</p>}
        </div>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          onClick={onClear}
        >
          Clear
        </button>
      </div>
      <dl className="space-y-1.5 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">Source</dt>
          <dd>{source?.label ?? edge.source}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Target</dt>
          <dd>{target?.label ?? edge.target}</dd>
        </div>
        {edge.direction && (
          <div>
            <dt className="text-xs text-muted-foreground">Direction</dt>
            <dd>{formatLabel(edge.direction)}</dd>
          </div>
        )}
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Confidence</dt>
          <dd className="tabular-nums">{formatConfidence(edge.confidence) ?? "—"}</dd>
        </div>
      </dl>
    </aside>
  );
}

function GraphReady({
  view,
  focusRef,
}: {
  view: KnowledgeGraphViewModel;
  focusRef?: string | null;
}) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [categoryFilter, setCategoryFilter] = useState<Set<GraphCategory> | null>(null);
  const [relFilter, setRelFilter] = useState<Set<string> | null>(null);
  const [minConfidence, setMinConfidence] = useState<number | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);

  useEffect(() => {
    if (!focusRef) return;
    const nodeId = resolveGraphNodeId(view, focusRef);
    if (!nodeId) return;
    setFocusNodeId(nodeId);
    setSelection({ kind: "node", id: nodeId });
  }, [focusRef, view]);

  const categories = useMemo(() => uniqueCategories(view), [view]);
  const relationships = useMemo(() => uniqueRelationships(view), [view]);

  const filtered = useMemo(
    () =>
      filterKnowledgeGraph(view, {
        query: deferredQuery,
        categories: categoryFilter,
        relationships: relFilter,
        minConfidence,
      }),
    [view, deferredQuery, categoryFilter, relFilter, minConfidence],
  );

  const emptyGraph = view.nodes.length === 0 && view.edges.length === 0;

  if (view.skipped) {
    return (
      <div className="space-y-4">
        <SummaryStrip view={view} />
        <section className="rounded-xl border border-border bg-muted/20 px-4 py-5 space-y-2">
          <h2 className="text-sm font-medium">Knowledge graph skipped</h2>
          <p className="text-sm text-foreground/85">
            {view.skipReason ?? "Graph construction was skipped for this document."}
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SummaryStrip view={view} />

      {view.warnings.length > 0 && (
        <ul className="space-y-2" role="list" aria-label="Graph warnings">
          {view.warnings.map((msg) => (
            <li
              key={msg}
              className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-sem-warn" aria-hidden />
              <span>{msg}</span>
            </li>
          ))}
        </ul>
      )}

      {emptyGraph ? (
        <p className="rounded-xl border border-border bg-muted/20 px-4 py-6 text-sm text-muted-foreground" role="status">
          No graph relationships were generated.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            <div className="relative flex-1">
              <label htmlFor="graph-search" className="sr-only">
                Search nodes and relationships
              </label>
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <input
                id="graph-search"
                type="search"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setFocusNodeId(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && filtered.matchedNodeIds.size > 0) {
                    const first = [...filtered.matchedNodeIds][0];
                    setSelection({ kind: "node", id: first });
                    setFocusNodeId(first);
                  }
                }}
                placeholder="Search labels, metadata, relationships…"
                className={cn(
                  "w-full rounded-xl border border-border bg-card py-2.5 pl-9 pr-3 text-sm",
                  "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                )}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="text-xs text-muted-foreground inline-flex items-center gap-1.5">
                Min confidence
                <select
                  className="rounded-lg border border-border bg-card px-2 py-1.5 text-xs text-foreground"
                  value={minConfidence ?? ""}
                  onChange={(e) =>
                    setMinConfidence(e.target.value === "" ? null : Number(e.target.value))
                  }
                >
                  <option value="">Any</option>
                  <option value="0.4">≥ 40%</option>
                  <option value="0.6">≥ 60%</option>
                  <option value="0.8">≥ 80%</option>
                </select>
              </label>
            </div>
          </div>

          {categories.length > 0 && (
            <fieldset className="space-y-1.5">
              <legend className="text-xs text-muted-foreground">Node categories</legend>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((c) => {
                  const on = categoryFilter == null || categoryFilter.has(c);
                  return (
                    <button
                      key={c}
                      type="button"
                      aria-pressed={on && categoryFilter != null}
                      className={cn(
                        "rounded-md border px-2 py-0.5 text-xs",
                        on && categoryFilter != null
                          ? "border-foreground bg-foreground text-background"
                          : "border-border bg-card text-foreground",
                      )}
                      onClick={() => {
                        setCategoryFilter((prev) => {
                          if (prev == null) return new Set([c]);
                          const next = new Set(prev);
                          if (next.has(c)) next.delete(c);
                          else next.add(c);
                          return next.size === 0 || next.size === categories.length ? null : next;
                        });
                      }}
                    >
                      {formatLabel(c)}
                    </button>
                  );
                })}
                {categoryFilter != null && (
                  <button
                    type="button"
                    className="text-xs text-muted-foreground underline"
                    onClick={() => setCategoryFilter(null)}
                  >
                    Clear
                  </button>
                )}
              </div>
            </fieldset>
          )}

          {relationships.length > 0 && (
            <fieldset className="space-y-1.5">
              <legend className="text-xs text-muted-foreground">Relationships</legend>
              <div className="flex flex-wrap gap-1.5">
                {relationships.map((r) => {
                  const on = relFilter == null || relFilter.has(r);
                  return (
                    <button
                      key={r}
                      type="button"
                      aria-pressed={on && relFilter != null}
                      className={cn(
                        "rounded-md border px-2 py-0.5 text-xs",
                        on && relFilter != null
                          ? "border-foreground bg-foreground text-background"
                          : "border-border bg-card text-foreground",
                      )}
                      onClick={() => {
                        setRelFilter((prev) => {
                          if (prev == null) return new Set([r]);
                          const next = new Set(prev);
                          if (next.has(r)) next.delete(r);
                          else next.add(r);
                          return next.size === 0 || next.size === relationships.length
                            ? null
                            : next;
                        });
                      }}
                    >
                      {formatLabel(r)}
                    </button>
                  );
                })}
                {relFilter != null && (
                  <button
                    type="button"
                    className="text-xs text-muted-foreground underline"
                    onClick={() => setRelFilter(null)}
                  >
                    Clear
                  </button>
                )}
              </div>
            </fieldset>
          )}

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
            <GraphCanvas
              nodes={filtered.nodes}
              edges={filtered.edges}
              matchedNodeIds={filtered.matchedNodeIds}
              selection={selection}
              onSelect={setSelection}
              focusNodeId={focusNodeId}
            />
            <DetailPanel view={view} selection={selection} onClear={() => setSelection(null)} />
          </div>

          {deferredQuery.trim() && filtered.matchedNodeIds.size > 0 && (
            <div className="space-y-1">
              <SectionHeading>Search hits</SectionHeading>
              <ul className="flex flex-wrap gap-1.5" role="list">
                {filtered.nodes
                  .filter((n) => filtered.matchedNodeIds.has(n.id))
                  .slice(0, 12)
                  .map((n) => (
                    <li key={n.key}>
                      <button
                        type="button"
                        className="rounded-md border border-border bg-card px-2 py-0.5 text-xs hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => {
                          setSelection({ kind: "node", id: n.id });
                          setFocusNodeId(n.id);
                        }}
                      >
                        {n.label}
                      </button>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </>
      )}

      {view.errors.length > 0 && (
        <ul className="space-y-2" role="list">
          {view.errors.map((msg) => (
            <li
              key={msg}
              className="flex gap-2 rounded-lg border border-sem-error/30 bg-sem-error/5 px-3 py-2 text-sm text-sem-error"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{msg}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function GraphLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading knowledge graph">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  );
}

/**
 * Knowledge Graph tab — read-only graph from knowledge_graph (M9).
 * Bound to GET …/phases/knowledge_graph via M1 hooks.
 */
export function PaperKnowledgeGraphTab({
  fileId,
  metaStatus,
  focusRef,
}: {
  fileId: number;
  metaStatus?: string | null;
  focusRef?: string | null;
}) {
  const { pipeline, derived, isLoading: pipelineLoading, isError: pipelineError, error: pipelineErr } =
    usePipeline(fileId);

  const hasPhase =
    pipeline != null &&
    (pipeline.phases.includes("knowledge_graph") ||
      "knowledge_graph" in (pipeline.phase_results ?? {}));

  const phaseQuery = usePipelinePhase(fileId, "knowledge_graph", {
    enabled: hasPhase,
  });

  const view = useMemo(() => {
    const raw = phaseQuery.data?.result ?? pipeline?.phase_results?.knowledge_graph ?? null;
    return mapKnowledgeGraph(raw);
  }, [phaseQuery.data, pipeline]);

  const waitingOnPipeline =
    derived.isQueued ||
    derived.isRunning ||
    metaStatus === "pending" ||
    metaStatus === "running";

  const loading =
    pipelineLoading ||
    (hasPhase && phaseQuery.isLoading && !view) ||
    (waitingOnPipeline && !view && !derived.isError);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AiStateBadge derived={derived} metaStatus={metaStatus} />
        </div>
        <GraphLoading />
      </div>
    );
  }

  if (pipelineError || (hasPhase && phaseQuery.isError && !view)) {
    const err = phaseQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Knowledge graph is not available for this paper yet."
        : err.details || err.code
      : "Could not load knowledge graph.";
    return (
      <div className="space-y-4">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <div
          role="alert"
          className="flex gap-2 rounded-xl border border-sem-error/30 bg-sem-error/5 px-4 py-3 text-sm text-sem-error"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{message}</span>
        </div>
      </div>
    );
  }

  if (!view || !view.hasContent) {
    return (
      <div className="space-y-4">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <EmptyState
          icon={<Network className="size-8" />}
          title="No knowledge graph yet"
          description={
            waitingOnPipeline
              ? "Knowledge graph construction is still running. This tab will fill in when the phase completes."
              : "No knowledge_graph result is available for this paper. Run Phase 1 analysis to build the graph."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Network className="size-3.5" aria-hidden />
          Knowledge graph
        </span>
      </div>
      <GraphReady view={view} focusRef={focusRef} />
    </div>
  );
}
