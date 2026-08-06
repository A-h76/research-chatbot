import { useMemo, useRef, type KeyboardEvent, type RefObject } from "react";
import {
  EVIDENCE_MARKER_RE,
  selectedEvidenceMarkerId,
} from "../utils/citeDraftHelpers";
import { cn } from "@/lib/utils";

type Seg =
  | { kind: "text"; value: string }
  | { kind: "cite"; id: number; value: string };

function parseSegments(content: string): Seg[] {
  const parts: Seg[] = [];
  const re = new RegExp(EVIDENCE_MARKER_RE.source, "g");
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(content)) != null) {
    if (m.index > last) parts.push({ kind: "text", value: content.slice(last, m.index) });
    parts.push({ kind: "cite", id: Number(m[1]), value: m[0] });
    last = m.index + m[0].length;
  }
  if (last < content.length) parts.push({ kind: "text", value: content.slice(last) });
  if (parts.length === 0 && content.length === 0) return [];
  if (parts.length === 0) parts.push({ kind: "text", value: content });
  return parts;
}

const EDITOR_TYPE =
  "mx-auto h-full min-h-0 w-full max-w-[65ch] whitespace-pre-wrap break-words px-1 py-2 text-[15px] leading-[1.55] tracking-[-0.011em]";

export function WritingManuscriptEditor({
  value,
  onChange,
  onCiteSelect,
  selectedCiteId,
  disabled,
  editorRef,
  onKeyDown,
  className,
}: {
  value: string;
  onChange: (next: string) => void;
  onCiteSelect?: (evidenceId: number) => void;
  selectedCiteId?: number | null;
  disabled?: boolean;
  editorRef?: RefObject<HTMLTextAreaElement | null>;
  onKeyDown?: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  className?: string;
}) {
  const localRef = useRef<HTMLTextAreaElement>(null);
  const ref = editorRef ?? localRef;
  const segments = useMemo(() => parseSegments(value), [value]);

  function syncScroll() {
    const ta = ref.current;
    const overlay = ta?.previousElementSibling as HTMLElement | null;
    if (ta && overlay) {
      overlay.scrollTop = ta.scrollTop;
      overlay.scrollLeft = ta.scrollLeft;
    }
  }

  function notifyCiteFromSelection() {
    const el = ref.current;
    if (!el || !onCiteSelect) return;
    const eid = selectedEvidenceMarkerId(value, el.selectionStart, el.selectionEnd);
    if (eid != null) onCiteSelect(eid);
  }

  return (
    <div className={cn("relative mx-auto min-h-0 w-full max-w-[65ch] flex-1", className)}>
      <div
        className={cn(
          EDITOR_TYPE,
          "pointer-events-none absolute inset-0 overflow-auto text-foreground",
        )}
        aria-hidden
      >
        {segments.length === 0 ? (
          <span className="text-muted-foreground">
            Manuscript — write or paste your literature review. Click Write literature review to
            draft from evidence.
          </span>
        ) : (
          segments.map((seg, i) =>
            seg.kind === "text" ? (
              <span key={i}>{seg.value}</span>
            ) : (
              <button
                key={i}
                type="button"
                tabIndex={-1}
                className={cn(
                  "pointer-events-auto inline rounded-sm px-0.5 font-medium text-primary",
                  selectedCiteId === seg.id
                    ? "bg-primary/25 ring-1 ring-primary/40"
                    : "bg-primary/12 hover:bg-primary/20",
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onCiteSelect?.(seg.id);
                }}
              >
                {seg.value}
              </button>
            ),
          )
        )}
      </div>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={syncScroll}
        onSelect={notifyCiteFromSelection}
        onMouseUp={notifyCiteFromSelection}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder=""
        aria-label="Manuscript editor"
        className={cn(
          EDITOR_TYPE,
          "relative z-[1] h-full min-h-[16rem] resize-none border-0 bg-transparent caret-foreground outline-none focus:ring-0",
          "text-transparent",
        )}
        spellCheck
      />
    </div>
  );
}
