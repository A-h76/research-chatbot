/**
 * Citation insert picker for Writing desk (Subsystem #5 / Target M4).
 * Tabs: EvidenceObjects (grounded [#id]) | Library citations (resolve → evidence or parenthetical).
 */
import { useEffect, useMemo, useState } from "react";
import { Loader2, Quote, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { citationsApi } from "@/features/citations/api";
import { useCitations } from "@/features/citations/useCitations";
import { evidenceApi } from "@/features/evidence/api";
import type { EvidenceObjectDTO } from "@/features/evidence/types";
import { cn } from "@/lib/utils";

export type CiteInsertPayload = {
  insertText: string;
  evidenceId: number | null;
  citationId: number | null;
  grounded: boolean;
  preview?: string;
};

type Tab = "evidence" | "library";

export function CitationInsertPicker({
  open,
  onClose,
  projectId,
  onInsert,
  className,
}: {
  open: boolean;
  onClose: () => void;
  projectId: number;
  onInsert: (payload: CiteInsertPayload) => void | Promise<void>;
  className?: string;
}) {
  const [tab, setTab] = useState<Tab>("evidence");
  const [q, setQ] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<EvidenceObjectDTO[]>([]);
  const [evStatus, setEvStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");

  const citationsQuery = useCitations({
    project_id: projectId,
    q: q.trim() || undefined,
  });

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setEvStatus("loading");
    evidenceApi
      .list(projectId, { status: "accepted" })
      .then((res) => {
        if (cancelled) return;
        setEvidence(res.items || []);
        setEvStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setEvidence([]);
        setEvStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [open, projectId]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filteredEvidence = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return evidence;
    return evidence.filter((e) => {
      const hay = `${e.claim || ""} ${e.quote || ""} ${e.id}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [evidence, q]);

  if (!open) return null;

  const insertEvidence = async (ev: EvidenceObjectDTO) => {
    setBusyId(`e-${ev.id}`);
    try {
      await onInsert({
        insertText: `[#${ev.id}]`,
        evidenceId: ev.id,
        citationId: null,
        grounded: true,
        preview: ev.claim || ev.quote || undefined,
      });
      onClose();
    } finally {
      setBusyId(null);
    }
  };

  const insertCitation = async (citationId: number) => {
    setBusyId(`c-${citationId}`);
    try {
      const resolved = await citationsApi.resolveEvidence(citationId, projectId);
      await onInsert({
        insertText: resolved.insert_text,
        evidenceId: resolved.evidence_id,
        citationId,
        grounded: resolved.grounded,
        preview: resolved.matches?.[0]?.claim || resolved.parenthetical,
      });
      onClose();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card shadow-md",
        className,
      )}
      role="dialog"
      aria-label="Insert citation"
    >
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <p className="text-[12px] font-medium text-foreground">Insert citation</p>
        <Button type="button" size="sm" variant="ghost" className="h-7 text-[11px]" onClick={onClose}>
          Esc
        </Button>
      </div>
      <div className="flex gap-1 border-b border-border px-2 pt-2">
        {(
          [
            ["evidence", "Evidence"],
            ["library", "Library"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={cn(
              "rounded-md px-2.5 py-1 text-[11px] font-medium",
              tab === id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted/50",
            )}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Search className="size-3.5 text-muted-foreground" />
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={tab === "evidence" ? "Search accepted evidence…" : "Search library citations…"}
          className="h-8 w-full bg-transparent text-[12px] outline-none"
        />
      </div>
      <ul className="max-h-56 overflow-y-auto p-1">
        {tab === "evidence" ? (
          evStatus === "loading" ? (
            <li className="flex items-center gap-2 px-2 py-3 text-[11px] text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" /> Loading evidence…
            </li>
          ) : filteredEvidence.length === 0 ? (
            <li className="px-2 py-3 text-[11px] text-muted-foreground">
              No accepted EvidenceObjects. Extract and accept evidence first.
            </li>
          ) : (
            filteredEvidence.map((ev) => (
              <li key={ev.id}>
                <button
                  type="button"
                  disabled={busyId != null}
                  className="flex w-full flex-col gap-0.5 rounded-md px-2 py-2 text-left hover:bg-muted/60"
                  onClick={() => void insertEvidence(ev)}
                >
                  <span className="text-[11px] font-medium text-foreground">
                    #{ev.id}
                    {ev.page != null ? ` · p.${ev.page}` : ""}
                    {busyId === `e-${ev.id}` ? " · inserting…" : ""}
                  </span>
                  <span className="line-clamp-2 text-[11px] text-muted-foreground">
                    {ev.claim || ev.quote || "(no claim)"}
                  </span>
                </button>
              </li>
            ))
          )
        ) : citationsQuery.isLoading ? (
          <li className="flex items-center gap-2 px-2 py-3 text-[11px] text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Loading citations…
          </li>
        ) : (citationsQuery.data || []).length === 0 ? (
          <li className="px-2 py-3 text-[11px] text-muted-foreground">
            No library citations. Add some on the Citations page.
          </li>
        ) : (
          (citationsQuery.data || []).map((c) => (
            <li key={c.id}>
              <button
                type="button"
                disabled={busyId != null}
                className="flex w-full flex-col gap-0.5 rounded-md px-2 py-2 text-left hover:bg-muted/60"
                onClick={() => void insertCitation(c.id)}
              >
                <span className="flex items-center gap-1 text-[11px] font-medium text-foreground">
                  <Quote className="size-3" />
                  {(c.authors || "Unknown").split(";")[0]}
                  {c.year ? ` (${c.year})` : ""}
                  {busyId === `c-${c.id}` ? " · resolving…" : ""}
                </span>
                <span className="line-clamp-2 text-[11px] text-muted-foreground">{c.title}</span>
                <span className="text-[10px] text-muted-foreground">{c.apa || c.ieee}</span>
              </button>
            </li>
          ))
        )}
      </ul>
      <p className="border-t border-border px-3 py-2 text-[10px] text-muted-foreground">
        Grounded inserts use [#id] markers (Reviewer-validated). Library cites resolve to evidence when
        DOI/title matches an accepted object.
      </p>
    </div>
  );
}
