import { useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

const ROLES = [
  { id: "student", label: "Student" },
  { id: "researcher", label: "Researcher" },
  { id: "professor", label: "Professor" },
  { id: "industry", label: "Industry" },
] as const;

const FIELDS = [
  { id: "ai", label: "AI" },
  { id: "medicine", label: "Medicine" },
  { id: "physics", label: "Physics" },
  { id: "economics", label: "Economics" },
  { id: "biology", label: "Biology" },
  { id: "chemistry", label: "Chemistry" },
  { id: "cs", label: "Computer Science" },
  { id: "engineering", label: "Engineering" },
  { id: "social", label: "Social Sciences" },
  { id: "other", label: "Other" },
] as const;

const GOALS = [
  { id: "publish", label: "Publish papers" },
  { id: "thesis", label: "Thesis" },
  { id: "lit_review", label: "Literature review" },
  { id: "discover", label: "Discover papers" },
  { id: "write", label: "Write research" },
] as const;

const EXPERIENCE = [
  { id: "beginner", label: "Beginner" },
  { id: "intermediate", label: "Intermediate" },
  { id: "advanced", label: "Advanced" },
] as const;

const STEPS = 7;

export function OnboardingWizard({ me }: { me: Me }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [role, setRole] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const [goal, setGoal] = useState("");
  const [experience, setExperience] = useState("");
  const [institution, setInstitution] = useState("");
  const [busy, setBusy] = useState(false);

  function toggleField(id: string) {
    setFields((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id].slice(0, 6),
    );
  }

  async function finish(opts: { skipped?: boolean } = {}) {
    setBusy(true);
    try {
      await api.post("/api/onboarding/complete", {
        skipped: Boolean(opts.skipped),
        research_role: role || undefined,
        research_fields: fields,
        research_goal: goal || (opts.skipped ? "explore" : undefined),
        experience_level: experience || undefined,
        institution: institution.trim() || undefined,
      });
      await qc.invalidateQueries({ queryKey: ["me"] });
    } finally {
      setBusy(false);
    }
  }

  const firstName = (me.name || "").trim().split(/\s+/)[0];

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-background/92 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-8 shadow-xl">
        <div className="mb-6 flex gap-1.5">
          {Array.from({ length: STEPS }).map((_, i) => (
            <span
              key={i}
              className={cn(
                "h-1 flex-1 rounded-full",
                i <= step ? "bg-primary" : "bg-muted",
              )}
            />
          ))}
        </div>

        {step === 0 && (
          <div className="space-y-5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Welcome{firstName ? `, ${firstName}` : ""}
            </p>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Welcome to Dhund
            </h2>
            <p className="text-[14px] leading-relaxed text-muted-foreground">
              Research Operating System — papers, evidence, writing, and export in one
              workspace.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" disabled={busy} onClick={() => finish({ skipped: true })}>
                Skip
              </Button>
              <Button disabled={busy} onClick={() => setStep(1)}>
                Continue <ArrowRight className="size-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <StepFrame
            title="Who are you?"
            onBack={() => setStep(0)}
            onNext={() => setStep(2)}
            busy={busy}
            nextDisabled={!role}
          >
            <ChoiceGrid
              options={ROLES}
              value={role}
              onChange={setRole}
            />
          </StepFrame>
        )}

        {step === 2 && (
          <StepFrame
            title="Research fields"
            subtitle="Select one or more."
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
            busy={busy}
            nextDisabled={fields.length === 0}
          >
            <div className="grid grid-cols-2 gap-2">
              {FIELDS.map((f) => {
                const active = fields.includes(f.id);
                return (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => toggleField(f.id)}
                    className={cn(
                      "rounded-xl border px-3 py-2.5 text-left text-[13px] transition-colors",
                      active
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border text-muted-foreground hover:bg-muted/40",
                    )}
                  >
                    <span className="inline-flex items-center gap-2">
                      {active && <Check className="size-3.5 text-primary" />}
                      {f.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </StepFrame>
        )}

        {step === 3 && (
          <StepFrame
            title="Research goal"
            onBack={() => setStep(2)}
            onNext={() => setStep(4)}
            busy={busy}
            nextDisabled={!goal}
          >
            <ChoiceGrid options={GOALS} value={goal} onChange={setGoal} />
          </StepFrame>
        )}

        {step === 4 && (
          <StepFrame
            title="Experience"
            onBack={() => setStep(3)}
            onNext={() => setStep(5)}
            busy={busy}
            nextDisabled={!experience}
          >
            <ChoiceGrid options={EXPERIENCE} value={experience} onChange={setExperience} />
          </StepFrame>
        )}

        {step === 5 && (
          <StepFrame
            title="Upload your first paper"
            subtitle="You can do this now or skip and start from the library."
            onBack={() => setStep(4)}
            onNext={() => setStep(6)}
            busy={busy}
            nextLabel="Continue"
            secondaryLabel="Skip for now"
            onSecondary={() => setStep(6)}
          >
            <label className="block text-[13px] font-medium text-foreground">
              Institution or topic (optional)
              <input
                className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-[14px] outline-none focus:ring-2 focus:ring-primary/30"
                placeholder="e.g. Oxford · PEGylated nanoparticles"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                maxLength={200}
              />
            </label>
            <Button
              className="mt-3 w-full"
              variant="outline"
              onClick={() => {
                window.location.href = "/library#import";
              }}
            >
              Open library to upload
            </Button>
          </StepFrame>
        )}

        {step === 6 && (
          <div className="space-y-5">
            <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">
              ✓
            </div>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              You&apos;re ready
            </h2>
            <p className="text-[14px] leading-relaxed text-muted-foreground">
              Launch Dhund and continue your literature review from a personalized Research OS home.
            </p>
            <Button className="w-full" disabled={busy} onClick={() => finish()}>
              Launch Dhund
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function StepFrame({
  title,
  subtitle,
  children,
  onBack,
  onNext,
  busy,
  nextDisabled,
  nextLabel = "Continue",
  secondaryLabel,
  onSecondary,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onBack: () => void;
  onNext: () => void;
  busy: boolean;
  nextDisabled?: boolean;
  nextLabel?: string;
  secondaryLabel?: string;
  onSecondary?: () => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">{title}</h2>
        {subtitle ? (
          <p className="mt-1 text-[13px] text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
      {children}
      <div className="flex justify-between gap-2 pt-2">
        <Button variant="ghost" onClick={onBack} disabled={busy}>
          Back
        </Button>
        <div className="flex gap-2">
          {secondaryLabel && onSecondary ? (
            <Button variant="ghost" onClick={onSecondary} disabled={busy}>
              {secondaryLabel}
            </Button>
          ) : null}
          <Button disabled={busy || nextDisabled} onClick={onNext}>
            {nextLabel} <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function ChoiceGrid({
  options,
  value,
  onChange,
}: {
  options: readonly { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="grid gap-2">
      {options.map((o) => {
        const active = value === o.id;
        return (
          <button
            key={o.id}
            type="button"
            onClick={() => onChange(o.id)}
            className={cn(
              "rounded-xl border px-3 py-3 text-left text-[13px] transition-colors",
              active
                ? "border-primary bg-primary/5 font-medium text-foreground"
                : "border-border text-muted-foreground hover:bg-muted/40",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
