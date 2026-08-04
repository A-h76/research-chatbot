import { useEffect, useMemo, useRef, useState } from "react";
import { IconCloud } from "@/components/ui/icon-cloud";
import { BeamCanvas, FlowNode } from "./FlowPrimitives";
import { cn } from "@/lib/utils";

/** High-signal research ecosystem marks — denser cloud, ≤16. */
export const ECOSYSTEM_CLOUD_IMAGES = [
  "/static/brands/pubmed.svg",
  "/static/brands/arxiv.svg",
  "/static/brands/openalex.png",
  "/static/brands/orcid.svg",
  "/static/brands/crossref.svg",
  "/static/brands/semanticscholar.png",
  "/static/brands/zotero.svg",
  "/static/brands/mendeley.svg",
  "/static/brands/googledrive.svg",
  "/static/brands/microsoftonedrive.svg",
  "/static/brands/dropbox.svg",
  "/static/brands/bibtex.svg",
  "/static/brands/ris.svg",
  "/static/brands/paperpile.svg",
  "/static/brands/jabref.png",
  "/static/brands/readcube.svg",
] as const;

const FLOW_CYCLES = [
  { source: "PubMed", mid: "Dhund", dest: "Evidence" },
  { source: "OpenAlex", mid: "Dhund", dest: "Analysis" },
  { source: "Zotero", mid: "Dhund", dest: "Library" },
  { source: "Google Drive", mid: "Dhund", dest: "Writing" },
  { source: "ORCID", mid: "Dhund", dest: "Evidence" },
] as const;

const CATEGORIES = [
  {
    id: "discover",
    title: "Discover",
    items: ["PubMed", "arXiv", "OpenAlex", "Europe PMC", "Crossref", "ORCID"],
  },
  {
    id: "store",
    title: "Store",
    items: ["Google Drive", "OneDrive", "Dropbox"],
  },
  {
    id: "references",
    title: "References",
    items: ["Zotero", "Mendeley", "BibTeX / RIS"],
  },
] as const;

function EcosystemFlowStrip({
  source,
  mid,
  dest,
}: {
  source: string;
  mid: string;
  dest: string;
}) {
  const a = useRef<HTMLDivElement>(null);
  const b = useRef<HTMLDivElement>(null);
  const c = useRef<HTMLDivElement>(null);
  const beams = useMemo(
    () => [
      { from: a, to: b, delay: 0 },
      { from: b, to: c, delay: 0.35 },
    ],
    [],
  );

  return (
    <BeamCanvas beams={beams} className="min-h-[4.5rem]">
      <div className="flex flex-wrap items-center justify-center gap-3 px-2 py-2">
        <FlowNode ref={a} label={source} sub="source" />
        <FlowNode ref={b} label={mid} sub="hub" active />
        <FlowNode ref={c} label={dest} sub="research" />
      </div>
    </BeamCanvas>
  );
}

/**
 * Research Ecosystem — Magic UI–style Icon Cloud (no center logo).
 * Static until hover; play/pause chrome hidden.
 */
export function ResearchEcosystemCloud({
  className,
  compact,
  showCategories = true,
}: {
  className?: string;
  compact?: boolean;
  showCategories?: boolean;
}) {
  const [cycle, setCycle] = useState(0);
  const active = FLOW_CYCLES[cycle % FLOW_CYCLES.length]!;

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const id = window.setInterval(() => {
      setCycle((c) => (c + 1) % FLOW_CYCLES.length);
    }, 4200);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className={cn("w-full", className)}>
      <div className="relative mx-auto flex max-w-xl flex-col items-center">
        <IconCloud
          images={[...ECOSYSTEM_CLOUD_IMAGES]}
          showControl={false}
          animateOnHover
          width={compact ? 340 : 420}
          height={compact ? 340 : 420}
        />

        <p className="mt-1 max-w-sm text-center text-[12px] text-muted-foreground">
          Everything researchers use connects here — then enters one evidence-first pipeline.
        </p>

        <div className="mt-4 w-full rounded-xl border border-border/70 bg-card/40 px-2 py-2">
          <p className="mb-1 text-center text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Source → Dhund → research
          </p>
          <EcosystemFlowStrip key={`${active.source}-${active.dest}`} {...active} />
        </div>
      </div>

      {showCategories ? (
        <div className="mx-auto mt-8 grid max-w-3xl gap-4 sm:grid-cols-3">
          {CATEGORIES.map((cat) => (
            <div key={cat.id} className="text-center sm:text-left">
              <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                {cat.title}
              </h3>
              <ul className="mt-2 space-y-1 text-[13px] text-foreground/90">
                {cat.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
