/**
 * Verify panel for grounded Literature Review drafts (Sprint B).
 * Paragraph → marker hover → evidence cards → Accept | Revise
 */
import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type {
  GroundedWritingBinding,
  GroundedWritingResult,
  GroundedWritingSection,
  WritingReview,
} from "@/features/evidence/hooks/useGroundedWriting";

const MARKER_RE = /\[#(\d+)\]/g;

function bindingsById(section: GroundedWritingSection): Map<number, GroundedWritingBinding> {
  const map = new Map<number, GroundedWritingBinding>();
  for (const b of section.bindings || []) {
    map.set(b.evidence_id, b);
  }
  for (const c of section.citations || []) {
    if (!map.has(c.evidence_id)) {
      map.set(c.evidence_id, {
        evidence_id: c.evidence_id,
        file_id: c.file_id,
        page: c.page,
        claim: c.claim,
        quote: c.quote,
        confidence_band: c.confidence_band,
      });
    }
  }
  return map;
}

function ParagraphWithMarkers({
  text,
  bindingMap,
  activeId,
  onHover,
  onSelect,
}: {
  text: string;
  bindingMap: Map<number, GroundedWritingBinding>;
  activeId: number | null;
  onHover: (id: number | null) => void;
  onSelect: (id: number) => void;
}) {
  const parts = useMemo(() => {
    const out: Array<{ type: "text"; value: string } | { type: "mark"; id: number }> = [];
    let last = 0;
    const re = new RegExp(MARKER_RE.source, "g");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) out.push({ type: "text", value: text.slice(last, m.index) });
      out.push({ type: "mark", id: Number(m[1]) });
      last = m.index + m[0].length;
    }
    if (last < text.length) out.push({ type: "text", value: text.slice(last) });
    return out;
  }, [text]);

  return (
    <p className="whitespace-pre-wrap text-[15px] leading-[1.75] tracking-[-0.01em] text-foreground">
      {parts.map((part, i) =>
        part.type === "text" ? (
          <span key={i}>{part.value}</span>
        ) : (
          <button
            key={`${part.id}-${i}`}
            type="button"
            className={cn(
              "mx-0.5 inline rounded px-1 py-0.5 text-[11px] font-medium underline-offset-2 transition-colors",
              bindingMap.has(part.id)
                ? "bg-emerald-500/15 text-emerald-800 underline dark:text-emerald-200"
                : "bg-amber-500/15 text-amber-800 dark:text-amber-200",
              activeId === part.id && "ring-1 ring-primary/40",
            )}
            title={
              bindingMap.get(part.id)?.claim ||
              (bindingMap.has(part.id) ? `Evidence #${part.id}` : `Unknown #${part.id}`)
            }
            onMouseEnter={() => onHover(part.id)}
            onMouseLeave={() => onHover(null)}
            onFocus={() => onHover(part.id)}
            onBlur={() => onHover(null)}
            onClick={() => onSelect(part.id)}
          >
            [#{part.id}]
          </button>
        ),
      )}
    </p>
  );
}

function EvidenceCard({ binding }: { binding: GroundedWritingBinding }) {
  return (
    <div className="rounded-md border border-border bg-background/80 p-2 text-[11px]">
      <p className="font-medium text-foreground">
        Evidence #{binding.evidence_id}
        {binding.page != null ? ` · p.${binding.page}` : ""}
        {binding.confidence_band ? ` · ${binding.confidence_band}` : ""}
      </p>
      {binding.claim ? <p className="mt-1 text-muted-foreground">{binding.claim}</p> : null}
      {binding.quote ? (
        <p className="mt-1 border-l-2 border-emerald-700/40 pl-2 italic text-muted-foreground">
          “{binding.quote}”
        </p>
      ) : null}
    </div>
  );
}

function SectionVerify({
  section,
  issues,
  accepted,
  onAccept,
  onRevise,
}: {
  section: GroundedWritingSection;
  issues: WritingReview["issues"];
  accepted: boolean;
  onAccept: () => void;
  onRevise: () => void;
}) {
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const reduceMotion = useReducedMotion();
  const bindingMap = useMemo(() => bindingsById(section), [section]);
  const activeId = selectedId ?? hoverId;
  const activeBinding = activeId != null ? bindingMap.get(activeId) : undefined;
  const sectionIssues = issues.filter((i) => i.section_id === section.id);

  if (section.status !== "ok" || !section.paragraph) return null;

  return (
    <div
      className={cn(
        "rounded-md border p-3",
        accepted ? "border-emerald-700/40 bg-emerald-500/5" : "border-border bg-card/40",
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {section.title || section.id}
          {section.confidence ? ` · ${section.confidence}` : ""}
          {accepted ? " · accepted" : ""}
        </p>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant={accepted ? "default" : "outline"}
            className="h-6 gap-1 px-2 text-[10px]"
            onClick={onAccept}
          >
            <Check className="size-3" /> Accept
          </Button>
          <Button size="sm" variant="ghost" className="h-6 gap-1 px-2 text-[10px]" onClick={onRevise}>
            <RefreshCw className="size-3" /> Revise
          </Button>
        </div>
      </div>

      <ParagraphWithMarkers
        text={section.paragraph}
        bindingMap={bindingMap}
        activeId={activeId}
        onHover={setHoverId}
        onSelect={setSelectedId}
      />

      <AnimatePresence mode="wait" initial={false}>
        {activeBinding ? (
          <motion.div
            key={activeBinding.evidence_id}
            initial={reduceMotion ? false : { opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, x: 10 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="mt-3 border-l-2 border-primary/40 pl-3"
          >
            <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Evidence
            </p>
            <EvidenceCard binding={activeBinding} />
          </motion.div>
        ) : (section.bindings?.length ?? 0) > 0 ? (
          <motion.div
            key="hint"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            className="mt-2"
          >
            <p className="text-[10px] text-muted-foreground">
              Click a [#id] marker to inspect evidence
            </p>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {sectionIssues.length ? (
        <ul className="mt-2 space-y-0.5 text-[10px] text-amber-800 dark:text-amber-200">
          {sectionIssues.map((issue, idx) => (
            <li key={`${issue.code}-${idx}`}>
              [{issue.severity}] {issue.message}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function GroundedDraftVerify({
  writing,
  onRevise,
  onAcceptAll,
}: {
  writing: GroundedWritingResult;
  onRevise: () => void;
  onAcceptAll?: (sectionIds: string[]) => void;
}) {
  const sections = (writing.sections || []).filter((s) => s.status === "ok" && s.paragraph);
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const issues = writing.review?.issues || [];

  const toggleAccept = (id: string) => {
    setAccepted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      onAcceptAll?.(Array.from(next));
      return next;
    });
  };

  if (!sections.length) {
    return (
      <p className="whitespace-pre-wrap leading-relaxed text-foreground">{writing.paragraph}</p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
        Verify · hover markers · accept or revise each section
      </p>
      {sections.map((sec) => (
        <SectionVerify
          key={sec.id}
          section={sec}
          issues={issues}
          accepted={accepted.has(sec.id)}
          onAccept={() => toggleAccept(sec.id)}
          onRevise={onRevise}
        />
      ))}
    </div>
  );
}

/** Persist paragraph↔evidence bindings for inserted grounded sections. */
export async function persistGroundedBindings(opts: {
  documentId: number;
  writing: GroundedWritingResult;
  createBinding: (
    documentId: number,
    body: {
      evidence_object_id: number;
      block_id?: string;
      selected_text?: string;
      relation?: string;
    },
  ) => Promise<unknown>;
}): Promise<{ saved: number; failed: number }> {
  const sections = (opts.writing.sections || []).filter((s) => s.status === "ok");
  let saved = 0;
  let failed = 0;
  const seen = new Set<string>();

  for (const sec of sections) {
    const text = (sec.paragraph || "").slice(0, 2000);
    const bindings = sec.bindings?.length
      ? sec.bindings
      : (sec.evidence_ids || []).map((id) => ({
          evidence_id: id,
          claim: "",
          quote: "",
        }));
    for (const b of bindings) {
      const key = `${sec.id}:${b.evidence_id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      try {
        await opts.createBinding(opts.documentId, {
          evidence_object_id: b.evidence_id,
          block_id: `writing_${sec.id}`,
          selected_text: text,
          relation: "supports",
        });
        saved += 1;
      } catch {
        failed += 1;
      }
    }
  }
  return { saved, failed };
}
