import { useMemo, useRef, type KeyboardEvent, type RefObject } from "react";
import {
  EVIDENCE_MARKER_RE,
  selectedEvidenceMarkerId,
} from "../utils/citeDraftHelpers";
import { cn } from "@/lib/utils";

/**
 * Overlay must render the same characters as the textarea (including markdown
 * markers and [#id] cites) so caret/selection stay aligned.
 */
function renderLine(
  line: string,
  lineKey: string,
  selectedCiteId: number | null | undefined,
  onCiteSelect?: (id: number) => void,
): React.ReactNode {
  const isH1 = /^#\s+/.test(line);
  const isH2 = /^##\s+/.test(line) && !/^###\s+/.test(line);
  const isH3 = /^###\s+/.test(line);

  const lineClass = cn(
    "whitespace-pre-wrap break-words",
    isH1 && "text-[1.35em] font-semibold tracking-tight",
    isH2 && "text-[1.15em] font-semibold tracking-tight",
    isH3 && "text-[1.05em] font-semibold",
  );

  const nodes: React.ReactNode[] = [];
  const re = new RegExp(EVIDENCE_MARKER_RE.source, "g");
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  const pushText = (chunk: string) => {
    if (!chunk) return;
    // Inline bold/italic while keeping markers visible (faint) for caret sync.
    const parts = chunk.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    for (const p of parts) {
      if (!p) continue;
      const bold = /^\*\*([^*]+)\*\*$/.exec(p);
      if (bold) {
        nodes.push(
          <span key={`${lineKey}-b-${i++}`}>
            <span className="text-transparent">**</span>
            <strong className="font-semibold text-foreground">{bold[1]}</strong>
            <span className="text-transparent">**</span>
          </span>,
        );
        continue;
      }
      const ital = /^\*([^*]+)\*$/.exec(p);
      if (ital) {
        nodes.push(
          <span key={`${lineKey}-i-${i++}`}>
            <span className="text-transparent">*</span>
            <em className="italic text-foreground">{ital[1]}</em>
            <span className="text-transparent">*</span>
          </span>,
        );
        continue;
      }
      // Heading markers: keep width, fade visually
      if (isH1 || isH2 || isH3) {
        const hm = /^(#{1,3}\s+)([\s\S]*)$/.exec(p);
        if (hm && last === 0 && nodes.length === 0) {
          nodes.push(
            <span key={`${lineKey}-h-${i++}`}>
              <span className="text-transparent">{hm[1]}</span>
              <span>{hm[2]}</span>
            </span>,
          );
          continue;
        }
      }
      // Color spans: show inner text colored, hide tags
      const withColor = p.split(/(<span style="color:[^"]+">|<\/span>)/g);
      for (const piece of withColor) {
        if (!piece) continue;
        const open = /^<span style="color:([^"]+)">$/.exec(piece);
        if (open) {
          nodes.push(
            <span key={`${lineKey}-co-${i++}`} className="text-transparent">
              {piece}
            </span>,
          );
          // following text until close handled as normal; we just hide tags
          continue;
        }
        if (piece === "</span>") {
          nodes.push(
            <span key={`${lineKey}-cc-${i++}`} className="text-transparent">
              {piece}
            </span>,
          );
          continue;
        }
        nodes.push(<span key={`${lineKey}-t-${i++}`}>{piece}</span>);
      }
    }
  };

  while ((m = re.exec(line)) != null) {
    if (m.index > last) pushText(line.slice(last, m.index));
    const id = Number(m[1]);
    nodes.push(
      <button
        key={`${lineKey}-cite-${i++}`}
        type="button"
        tabIndex={-1}
        className={cn(
          "pointer-events-auto inline rounded-sm px-0.5 font-medium",
          selectedCiteId === id
            ? "bg-primary text-primary-foreground ring-1 ring-primary/40"
            : "bg-primary/90 text-primary-foreground",
        )}
        onMouseDown={(e) => {
          e.preventDefault();
          onCiteSelect?.(id);
        }}
      >
        {m[0]}
      </button>,
    );
    last = m.index + m[0].length;
  }
  if (last < line.length) pushText(line.slice(last));
  if (nodes.length === 0) nodes.push(<span key={`${lineKey}-empty`}>{"\u00a0"}</span>);

  return <div className={lineClass}>{nodes}</div>;
}

const EDITOR_TYPE =
  "mx-auto h-full min-h-0 w-full max-w-[65ch] px-1 py-2 text-[15px] leading-[1.65] tracking-[-0.011em]";

export function WritingManuscriptEditor({
  value,
  onChange,
  onCiteSelect,
  selectedCiteId,
  disabled,
  editorRef,
  onKeyDown,
  onSelectionChange,
  className,
}: {
  value: string;
  onChange: (next: string) => void;
  onCiteSelect?: (evidenceId: number) => void;
  selectedCiteId?: number | null;
  disabled?: boolean;
  editorRef?: RefObject<HTMLTextAreaElement | null>;
  onKeyDown?: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSelectionChange?: (start: number, end: number) => void;
  className?: string;
}) {
  const localRef = useRef<HTMLTextAreaElement>(null);
  const ref = editorRef ?? localRef;
  const lines = useMemo(() => (value.length ? value.split("\n") : [""]), [value]);

  function syncScroll() {
    const ta = ref.current;
    const overlay = ta?.previousElementSibling as HTMLElement | null;
    if (ta && overlay) {
      overlay.scrollTop = ta.scrollTop;
      overlay.scrollLeft = ta.scrollLeft;
    }
  }

  function notifySelection() {
    const el = ref.current;
    if (!el) return;
    onSelectionChange?.(el.selectionStart, el.selectionEnd);
    if (!onCiteSelect) return;
    const eid = selectedEvidenceMarkerId(value, el.selectionStart, el.selectionEnd);
    if (eid != null) onCiteSelect(eid);
  }

  return (
    <div className={cn("relative mx-auto min-h-0 w-full max-w-[65ch] flex-1", className)}>
      <div
        className={cn(EDITOR_TYPE, "pointer-events-none absolute inset-0 overflow-auto text-foreground")}
        aria-hidden
      >
        {value.length === 0 ? (
          <span className="text-muted-foreground">
            Start writing your manuscript. Use the toolbar for Title, Heading 2, bold, and italic.
          </span>
        ) : (
          lines.map((line, idx) => (
            <div key={`line-${idx}`}>
              {renderLine(line, `L${idx}`, selectedCiteId, onCiteSelect)}
            </div>
          ))
        )}
      </div>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={syncScroll}
        onSelect={notifySelection}
        onMouseUp={notifySelection}
        onKeyUp={notifySelection}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder=""
        aria-label="Manuscript editor"
        className={cn(
          EDITOR_TYPE,
          "relative z-[1] h-full min-h-[16rem] resize-none border-0 bg-transparent caret-foreground outline-none focus:ring-0",
          "whitespace-pre-wrap break-words text-transparent",
        )}
        spellCheck
      />
    </div>
  );
}
