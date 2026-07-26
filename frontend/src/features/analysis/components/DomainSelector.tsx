import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

/**
 * Mirrors backend/ai/domain_registry.py's DomainRegistry.DOMAINS keys —
 * all 9, not just the 6 this component's own spec named. A paper can be
 * auto-detected (or explicitly set via the "Detected:" badge below) as
 * e.g. "chemistry" or "physics"; leaving those out of the dropdown would
 * mean the trigger renders blank for a real value the backend can send.
 * Labels here are short display names for a dropdown row, not the
 * backend's own longer `label` field (e.g. "Medical and Allied Health
 * Sciences").
 */
const DOMAIN_LABELS: Record<string, string> = {
  medical: "Medical",
  ai_ml: "AI / Machine Learning",
  biology: "Biology",
  psychology: "Psychology",
  engineering: "Engineering",
  social_sciences: "Social Sciences",
  chemistry: "Chemistry",
  physics: "Physics",
  general: "General",
};

const DOMAIN_KEYS = Object.keys(DOMAIN_LABELS);

// base-ui's Select supports `null` as a real value directly, but this
// component's own contract (`value: string | null` <-> Select's
// `value ?? ""`) uses "" as the dropdown's own selectable "auto" row,
// distinct from Select's separate placeholder-for-nothing-selected
// concept — there's always something selected here (auto, or a domain).
const AUTO_VALUE = "";

export interface DomainSelectorProps {
  /** Selected domain, or null for auto-detect. */
  value: string | null;
  onChange: (domain: string | null) => void;
  /** Shown as a badge once an analysis has run and detected a domain. */
  detectedDomain?: string | null;
  disabled?: boolean;
  className?: string;
}

function labelFor(domain: string): string {
  return DOMAIN_LABELS[domain] ?? domain;
}

export function DomainSelector({
  value,
  onChange,
  detectedDomain,
  disabled = false,
  className,
}: DomainSelectorProps) {
  const matchesSelection = detectedDomain != null && detectedDomain === value;

  const applyDetected = React.useCallback(() => {
    if (!disabled && detectedDomain) onChange(detectedDomain);
  }, [disabled, detectedDomain, onChange]);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Select
        value={value ?? AUTO_VALUE}
        onValueChange={(next) => onChange(next === AUTO_VALUE ? null : (next as string))}
        disabled={disabled}
      >
        <SelectTrigger aria-label="Select paper domain">
          {/* base-ui's Select.Value treats "" as its own placeholder
              state rather than resolving it to the Auto-detect item's
              label (verified: data-placeholder is set, rendered text is
              empty) — the `placeholder` prop is exactly the mechanism
              for this, and lines up with this component's own "null ->
              placeholder: Auto-detect" contract. */}
          <SelectValue placeholder="Auto-detect" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={AUTO_VALUE}>Auto-detect</SelectItem>
          {DOMAIN_KEYS.map((domain) => (
            <SelectItem key={domain} value={domain}>
              {labelFor(domain)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {detectedDomain && (
        <Badge
          variant="outline"
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-live="polite"
          aria-disabled={disabled}
          onClick={applyDetected}
          onKeyDown={(e: React.KeyboardEvent) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              applyDetected();
            }
          }}
          className={cn(
            "cursor-pointer font-normal",
            matchesSelection
              ? "border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300"
              : "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
            disabled && "pointer-events-none cursor-default opacity-50"
          )}
        >
          {matchesSelection
            ? `Auto-detected: ${labelFor(detectedDomain)}`
            : `Detected: ${labelFor(detectedDomain)}`}
        </Badge>
      )}
    </div>
  );
}
