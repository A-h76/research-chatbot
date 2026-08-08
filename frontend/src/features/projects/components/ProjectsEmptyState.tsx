import { Check, FileText, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useMe } from "@/features/profile/useMe";
import type { UserFile } from "@/types/api";

/** Calm editorial graphic — research workflow, not a fake UI widget. */
function ResearchWorkflowIllustration() {
  const stroke = "currentColor";
  const accent = "var(--color-primary, currentColor)";

  return (
    <svg
      viewBox="0 0 320 72"
      className="mx-auto h-16 w-full max-w-[320px] text-muted-foreground"
      role="img"
      aria-label="Papers flow into evidence, writing, then publish"
    >
      {/* Papers */}
      <g transform="translate(8, 14)">
        <rect
          x="4"
          y="2"
          width="28"
          height="36"
          rx="3"
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
          opacity="0.35"
        />
        <rect
          x="0"
          y="6"
          width="28"
          height="36"
          rx="3"
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
        />
        <line x1="6" y1="16" x2="22" y2="16" stroke={stroke} strokeWidth="1.25" opacity="0.55" />
        <line x1="6" y1="22" x2="20" y2="22" stroke={stroke} strokeWidth="1.25" opacity="0.45" />
        <line x1="6" y1="28" x2="18" y2="28" stroke={stroke} strokeWidth="1.25" opacity="0.35" />
      </g>
      <text
        x="22"
        y="68"
        textAnchor="middle"
        className="fill-current"
        style={{ fontSize: 9, fontWeight: 500, letterSpacing: "0.04em" }}
        opacity="0.7"
      >
        Papers
      </text>

      {/* Arrow */}
      <path
        d="M48 36 H72"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        opacity="0.45"
      />
      <path
        d="M68 32 L74 36 L68 40"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.45"
      />

      {/* Evidence — bookmark / quote mark */}
      <g transform="translate(86, 16)">
        <rect
          x="0"
          y="0"
          width="36"
          height="40"
          rx="3"
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
        />
        <path
          d="M10 12 H26 M10 20 H22"
          fill="none"
          stroke={stroke}
          strokeWidth="1.25"
          strokeLinecap="round"
          opacity="0.5"
        />
        <path
          d="M8 28 H20"
          fill="none"
          stroke={accent}
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.7"
        />
      </g>
      <text
        x="104"
        y="68"
        textAnchor="middle"
        className="fill-current"
        style={{ fontSize: 9, fontWeight: 500, letterSpacing: "0.04em" }}
        opacity="0.7"
      >
        Evidence
      </text>

      <path
        d="M134 36 H158"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        opacity="0.45"
      />
      <path
        d="M154 32 L160 36 L154 40"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.45"
      />

      {/* Writing — lines + pen tip */}
      <g transform="translate(172, 16)">
        <rect
          x="0"
          y="0"
          width="36"
          height="40"
          rx="3"
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
        />
        <path
          d="M8 14 H28 M8 22 H24 M8 30 H20"
          fill="none"
          stroke={stroke}
          strokeWidth="1.25"
          strokeLinecap="round"
          opacity="0.5"
        />
        <path
          d="M26 34 L32 28 L34 30 L28 36 Z"
          fill="none"
          stroke={accent}
          strokeWidth="1.25"
          strokeLinejoin="round"
          opacity="0.75"
        />
      </g>
      <text
        x="190"
        y="68"
        textAnchor="middle"
        className="fill-current"
        style={{ fontSize: 9, fontWeight: 500, letterSpacing: "0.04em" }}
        opacity="0.7"
      >
        Writing
      </text>

      <path
        d="M220 36 H244"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        opacity="0.45"
      />
      <path
        d="M240 32 L246 36 L240 40"
        fill="none"
        stroke={accent}
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.45"
      />

      {/* Publish — document rising / out */}
      <g transform="translate(258, 16)">
        <rect
          x="0"
          y="8"
          width="36"
          height="32"
          rx="3"
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
        />
        <path
          d="M18 4 V22"
          fill="none"
          stroke={accent}
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.75"
        />
        <path
          d="M12 12 L18 4 L24 12"
          fill="none"
          stroke={accent}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.75"
        />
        <path
          d="M8 32 H28"
          fill="none"
          stroke={stroke}
          strokeWidth="1.25"
          strokeLinecap="round"
          opacity="0.4"
        />
      </g>
      <text
        x="276"
        y="68"
        textAnchor="middle"
        className="fill-current"
        style={{ fontSize: 9, fontWeight: 500, letterSpacing: "0.04em" }}
        opacity="0.7"
      >
        Publish
      </text>
    </svg>
  );
}

export function ProjectsEmptyState({
  papers,
  selectedIds,
  onToggle,
  onCreate,
}: {
  papers: UserFile[];
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
  onCreate: () => void;
}) {
  const hasPapers = papers.length > 0;
  const selectedCount = selectedIds.size;
  const { data: me } = useMe();
  const focus =
    me?.onboarding?.institution?.trim() ||
    me?.onboarding?.research_focus?.trim() ||
    (me?.onboarding?.research_fields || []).join(", ");

  return (
    <div className="mx-auto flex max-w-lg flex-col items-center py-10 text-center sm:py-14">
      <div className="mb-8 w-full opacity-90">
        <ResearchWorkflowIllustration />
      </div>

      <h2 className="text-lg font-semibold tracking-tight text-text-primary">
        No projects yet
      </h2>
      <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-text-secondary">
        {focus
          ? `Continue “${focus}” — gather papers, extract evidence, write with citations, and publish when you’re ready.`
          : "Start a research effort — gather papers, extract evidence, write with citations, and publish when you’re ready."}
      </p>

      {hasPapers && (
        <div className="mt-7 w-full text-left">
          <p className="mb-1 text-center text-[12px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
            Imported papers
          </p>
          <p className="mb-3 text-center text-[12px] text-text-secondary">
            You already imported{" "}
            {papers.length === 1 ? "a paper" : `${papers.length} papers`}. Use{" "}
            {papers.length === 1 ? "it" : "these"} to start your first research.
          </p>
          <ul className="divide-y divide-border border-y border-border">
            {papers.map((p) => {
              const selected = selectedIds.has(p.id);
              const title = p.title || p.name;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => onToggle(p.id)}
                    className={cn(
                      "group flex w-full items-center gap-3 px-1 py-2.5 text-left transition-colors hover:bg-muted/25",
                      selected ? "opacity-100" : "opacity-70 hover:opacity-100",
                    )}
                    aria-pressed={selected}
                    title={
                      selected
                        ? "Included — click to leave out"
                        : "Click to include in your first research"
                    }
                  >
                    <Check
                      className={cn(
                        "size-3.5 shrink-0 transition-opacity",
                        selected ? "text-text-accent opacity-100" : "text-text-tertiary opacity-40",
                      )}
                      strokeWidth={2.5}
                      aria-hidden
                    />
                    <FileText className="size-3.5 shrink-0 text-text-tertiary" />
                    <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-text-primary">
                      {title}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {selectedCount === 0 ? (
            <p className="mt-2 text-center text-[11px] text-text-tertiary">
              No papers selected — you can still start empty.
            </p>
          ) : null}
        </div>
      )}

      <Button size="lg" className="mt-7 gap-1.5" onClick={onCreate}>
        <Plus className="size-4" />
        {hasPapers && selectedCount > 0
          ? "Start research"
          : "Start your first research"}
      </Button>

      <Link
        to="/"
        className="mt-5 text-[12px] text-text-secondary transition-colors hover:text-text-accent"
      >
        Need help choosing a topic? Ask Research Mentor →
      </Link>
    </div>
  );
}
