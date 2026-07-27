import * as React from "react";
import { ChevronDownIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface MetadataInputValue {
  title: string;
  authors: string;
  venue: string;
  year: string;
}

export interface MetadataInputProps {
  value: MetadataInputValue;
  onChange: (metadata: Partial<MetadataInputValue>) => void;
  disabled?: boolean;
  defaultOpen?: boolean;
  /** Optional auto-fill source — pre-populates any field that's still empty. */
  documentMetadata?: Partial<MetadataInputValue>;
}

const EMPTY: MetadataInputValue = { title: "", authors: "", venue: "", year: "" };
const YEAR_MIN = 1900;
const YEAR_MAX = 2100;

const FIELDS: { key: keyof MetadataInputValue; label: string; placeholder: string }[] = [
  { key: "title", label: "Title", placeholder: "e.g., Attention Is All You Need" },
  { key: "authors", label: "Authors", placeholder: "e.g., Vaswani et al." },
  { key: "venue", label: "Venue", placeholder: "e.g., NeurIPS" },
  { key: "year", label: "Year", placeholder: "e.g., 2017" },
];

function yearError(year: string): string | null {
  if (!year.trim()) return null;
  const n = Number(year);
  return Number.isInteger(n) && n >= YEAR_MIN && n <= YEAR_MAX
    ? null
    : `Enter a year between ${YEAR_MIN} and ${YEAR_MAX}`;
}

export function MetadataInput({
  value,
  onChange,
  disabled = false,
  defaultOpen = false,
  documentMetadata,
}: MetadataInputProps) {
  // Fills empty fields whenever documentMetadata (re)loads. `value`/`onChange`
  // are deliberately left out of the deps — this should only re-sync when
  // the document's own metadata changes, not on every keystroke in the form.
  React.useEffect(() => {
    if (!documentMetadata) return;
    const fill: Partial<MetadataInputValue> = {};
    for (const key of Object.keys(EMPTY) as (keyof MetadataInputValue)[]) {
      const incoming = documentMetadata[key];
      if (incoming && !value[key]) fill[key] = incoming;
    }
    if (Object.keys(fill).length > 0) onChange(fill);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentMetadata]);

  const handleChange =
    (key: keyof MetadataInputValue) => (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ [key]: e.target.value } as Partial<MetadataInputValue>);
    };

  // Trim on blur rather than on every keystroke, so typing a space between
  // words in Title/Authors/Venue doesn't get stripped back out mid-typing.
  const handleBlur =
    (key: keyof MetadataInputValue) => (e: React.FocusEvent<HTMLInputElement>) => {
      const trimmed = e.target.value.trim();
      if (trimmed !== e.target.value) onChange({ [key]: trimmed } as Partial<MetadataInputValue>);
    };

  const clearAll = () => onChange({ ...EMPTY });

  const yearErr = yearError(value.year);

  return (
    <Collapsible defaultOpen={defaultOpen} disabled={disabled}>
      <CollapsibleTrigger render={<Button type="button" variant="ghost" size="sm" className="gap-1.5 px-2" />}>
        Advanced Metadata
        <ChevronDownIcon className="size-4 transition-transform in-data-[panel-open]:rotate-180" />
      </CollapsibleTrigger>

      <CollapsibleContent className="pt-3">
        <div className="mb-2 flex justify-end">
          <Button
            type="button"
            variant="link"
            size="sm"
            className="h-auto p-0 text-xs"
            onClick={clearAll}
            disabled={disabled}
          >
            Clear all
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {FIELDS.map(({ key, label, placeholder }) => (
            <div key={key} className="grid gap-1.5">
              <Label htmlFor={`metadata-${key}`}>{label}</Label>
              <Input
                id={`metadata-${key}`}
                type={key === "year" ? "number" : "text"}
                min={key === "year" ? YEAR_MIN : undefined}
                max={key === "year" ? YEAR_MAX : undefined}
                value={value[key]}
                onChange={handleChange(key)}
                onBlur={handleBlur(key)}
                placeholder={placeholder}
                disabled={disabled}
                aria-invalid={key === "year" ? !!yearErr : undefined}
                aria-describedby={key === "year" && yearErr ? "metadata-year-error" : undefined}
              />
              {key === "year" && yearErr && (
                <p id="metadata-year-error" className="text-xs text-destructive">
                  {yearErr}
                </p>
              )}
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
