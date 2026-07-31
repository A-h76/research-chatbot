import { AlertCircle, Check, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DocumentAnalysisReport } from "./documentAnalysis";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

/** Educating health report — not an alarm list for non-IMRaD papers. */
export function DocumentAnalysisPanel({ report }: { report: DocumentAnalysisReport }) {
  if (!report.show) return null;

  return (
    <section aria-labelledby="structure-analysis-heading" className="space-y-3">
      <h2 id="structure-analysis-heading">
        <SectionHeading>Document Analysis</SectionHeading>
      </h2>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3 sm:px-5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Overall
          </p>
          <p className="mt-0.5 text-[15px] font-semibold tracking-tight text-foreground">
            {report.overallLabel}
          </p>
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            {report.overallDetail}
          </p>
        </div>

        {report.processingSignals.length > 0 && (
          <div className="border-b border-border px-4 py-3 sm:px-5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Processing
            </p>
            <ul className="mt-2 space-y-1.5" role="list">
              {report.processingSignals.map((s) => (
                <li
                  key={s.id}
                  className="flex items-start gap-2 text-[13px] text-foreground/90"
                >
                  {s.ok ? (
                    <Check
                      className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                      aria-hidden
                    />
                  ) : (
                    <Info
                      className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"
                      aria-hidden
                    />
                  )}
                  <span className="min-w-0">
                    <span className="font-medium">{s.label}</span>
                    {s.detail ? (
                      <span className="text-muted-foreground"> · {s.detail}</span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.processingProblems.length > 0 && (
          <div className="border-b border-border bg-sem-error/5 px-4 py-3 sm:px-5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-sem-error">
              Processing issues
            </p>
            <ul className="mt-2 space-y-2" role="list">
              {report.processingProblems.map((msg) => (
                <li
                  key={msg}
                  className="flex gap-2 text-[13px] text-sem-error"
                >
                  <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                  <span>{msg}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="px-4 py-3 sm:px-5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Structure
          </p>
          <p className="mt-0.5 text-[14px] font-semibold tracking-tight text-foreground">
            {report.structureTitle}
          </p>
          <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
            {report.structureSummary}
          </p>

          {(report.detected.length > 0 || report.notDetected.length > 0) && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {report.detected.length > 0 && (
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground">Detected</p>
                  <ul className="mt-1.5 space-y-1" role="list">
                    {report.detected.map((d) => (
                      <li
                        key={d}
                        className="flex items-center gap-1.5 text-[13px] text-foreground/85"
                      >
                        <Check
                          className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                          aria-hidden
                        />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {report.notDetected.length > 0 && (
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground">
                    Not labeled as
                  </p>
                  <ul className="mt-1.5 space-y-1" role="list">
                    {report.notDetected.map((d) => (
                      <li
                        key={d}
                        className="flex items-center gap-1.5 text-[13px] text-muted-foreground"
                      >
                        <span className="w-3.5 text-center text-[11px]" aria-hidden>
                          ·
                        </span>
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {report.structureKind === "narrative_review" && (
            <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">
              Expected outline for this genre: {report.expectedOutline.join(" · ")}. No
              action required.
            </p>
          )}

          {report.whyExplanation && (
            <div
              className={cn(
                "mt-3 flex gap-2 rounded-lg border border-border/80 bg-muted/30 px-3 py-2.5",
              )}
            >
              <Info
                className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"
                aria-hidden
              />
              <div className="min-w-0 text-[13px] leading-relaxed text-foreground/85">
                <p className="font-medium text-foreground">Why?</p>
                <p className="mt-0.5 text-muted-foreground">{report.whyExplanation}</p>
              </div>
            </div>
          )}

          {report.structureNotes.length > 0 && (
            <ul className="mt-3 space-y-1.5" role="list">
              {report.structureNotes.map((note) => (
                <li
                  key={note}
                  className="flex gap-2 text-[12px] text-muted-foreground"
                >
                  <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
