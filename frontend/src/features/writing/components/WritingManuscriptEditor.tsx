import { useMemo, useRef, type KeyboardEvent, type RefObject } from "react";
import {
  EVIDENCE_MARKER_RE,
  selectedEvidenceMarkerId,
} from "../utils/citeDraftHelpers";
import { cn } from "@/lib/utils";

/**
 * Overlay must keep the same glyph metrics as the textarea (identical font,
 * size, weight, letter-spacing, wrapping) so caret/selection stay aligned.
 * Visual polish that changes width (extra padding, larger headings) is avoided.
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

  // Keep metrics identical to the textarea — no size/weight changes on the line.
  const lineClass = "whitespace-pre-wrap break-words";

  const nodes: React.ReactNode[] = [];
  const re = new RegExp(EVIDENCE_MARKER_RE.source, "g");
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  const pushText = (chunk: string, color?: string) => {
    if (!chunk) return;
    const parts = chunk.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    for (const p of parts) {
      if (!p) continue;
      const bold = /^\*\*([^*]+)\*\*$/.exec(p);
      if (bold) {
        nodes.push(
          <span key={`${lineKey}-b-${i++}`} style={color ? { color } : undefined}>
            <span className="opacity-0">**</span>
            <span
              style={{
                // Fake bold without changing glyph advance (keeps caret synced).
                textShadow: "0.35px 0 0 currentColor, -0.35px 0 0 currentColor",
              }}
            >
              {bold[1]}
            </span>
            <span className="opacity-0">**</span>
          </span>,
        );
        continue;
      }
      const ital = /^\*([^*]+)\*$/.exec(p);
      if (ital) {
        nodes.push(
          <span key={`${lineKey}-i-${i++}`} style={color ? { color } : undefined}>
            <span className="opacity-0">*</span>
            <span className="italic [font-synthesis:none]">
              {ital[1]}
            </span>
            <span className="opacity-0">*</span>
          </span>,
        );
        continue;
      }
      if ((isH1 || isH2 || isH3) && last === 0 && nodes.length === 0) {
        const hm = /^(#{1,3}\s+)([\s\S]*)$/.exec(p);
        if (hm) {
          nodes.push(
            <span key={`${lineKey}-h-${i++}`}>
              <span className="opacity-0">{hm[1]}</span>
              <span style={color ? { color } : undefined}>{hm[2]}</span>
            </span>,
          );
          continue;
        }
      }
      nodes.push(
        <span key={`${lineKey}-t-${i++}`} style={color ? { color } : undefined}>
          {p}
        </span>,
      );
    }
  };

  /** Parse inline color spans while preserving tag character widths. */
  const pushColored = (chunk: string) => {
    const reColor =
      /<span style="color:([^"]+)">([\s\S]*?)<\/span>/g;
    let cLast = 0;
    let cm: RegExpExecArray | null;
    while ((cm = reColor.exec(chunk)) != null) {
      if (cm.index > cLast) pushText(chunk.slice(cLast, cm.index));
      const open = `<span style="color:${cm[1]}">`;
      const close = "</span>";
      nodes.push(
        <span key={`${lineKey}-co-${i++}`} className="opacity-0">
          {open}
        </span>,
      );
      pushText(cm[2], cm[1]);
      nodes.push(
        <span key={`${lineKey}-cc-${i++}`} className="opacity-0">
          {close}
        </span>,
      );
      cLast = cm.index + cm[0].length;
    }
    if (cLast < chunk.length) pushText(chunk.slice(cLast));
  };

  while ((m = re.exec(line)) != null) {
    if (m.index > last) pushColored(line.slice(last, m.index));
    const id = Number(m[1]);
    // No extra padding — padding shifts caret vs textarea glyphs.
    nodes.push(
      <button
        key={`${lineKey}-cite-${i++}`}
        type="button"
        tabIndex={-1}
        className={cn(
          "pointer-events-auto inline rounded-sm font-medium",
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
  if (last < line.length) pushColored(line.slice(last));
  if (nodes.length === 0) nodes.push(<span key={`${lineKey}-empty`}>{"\u00a0"}</span>);

  return <div className={lineClass}>{nodes}</div>;
}

/** Shared metrics for overlay + textarea — must stay identical. */
const EDITOR_TYPE =
  "box-border h-full min-h-0 w-full px-1 py-2 text-[15px] leading-[1.65] tracking-[-0.011em] whitespace-pre-wrap break-words";

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
  const overlayRef = useRef<HTMLDivElement>(null);
  const ref = editorRef ?? localRef;
  const lines = useMemo(() => (value.length ? value.split("\n") : [""]), [value]);

  function syncScroll() {
    const ta = ref.current;
    const overlay = overlayRef.current;
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
    <div
      className={cn(
        "relative mx-auto min-h-0 w-full max-w-[65ch] flex-1",
        className,
      )}
    >
      {/* Both layers absolute inset-0 so boxes match exactly (fixes caret drift). */}
      <div
        ref={overlayRef}
        className={cn(
          EDITOR_TYPE,
          "pointer-events-none absolute inset-0 overflow-auto text-foreground",
        )}
        aria-hidden
      >
        {value.length === 0 ? (
          <div className="space-y-3 text-muted-foreground">
            <p className="text-[15px] leading-[1.65]">Start writing…</p>
            <ul className="space-y-1.5 text-[13px] leading-relaxed text-muted-foreground/80">
              <li>Type naturally.</li>
              <li>Cite evidence as you draft.</li>
              <li>Select text to inspect supporting sources.</li>
              <li>The Writing Assistant adapts as you work.</li>
            </ul>
          </div>
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
        // Spellcheck underlines on transparent text look like floating glitches.
        spellCheck={false}
        className={cn(
          EDITOR_TYPE,
          "absolute inset-0 z-[1] min-h-[16rem] resize-none border-0 bg-transparent caret-foreground outline-none focus:ring-0",
          "text-transparent",
        )}
      />
    </div>
  );
}
