import { useState } from "react";
import { Segmented } from "../components/Segmented";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { loadResearchPrefs, saveResearchPrefs, type ResearchPrefs } from "../lib/researchPrefs";
import { toast } from "@/components/common/Toast";

function Row({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 border-b border-border py-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 pr-4">
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export function ResearchDefaultsSection() {
  const [prefs, setPrefs] = useState<ResearchPrefs>(() => loadResearchPrefs());

  function update(patch: Partial<ResearchPrefs>) {
    const next = saveResearchPrefs(patch);
    setPrefs(next);
    toast.success("Saved");
  }

  return (
    <div>
      <p className="mb-1 text-sm text-muted-foreground">
        Preferences for the evidence-first literature review path. Draft generation always uses{" "}
        <span className="font-medium text-foreground">accepted evidence only</span> — that gate is
        not optional.
      </p>

      <Row
        label="Show AI Compare"
        description="Narrative LLM compare/gaps under Research. Off by default — Evidence Matrix stays primary."
      >
        <Segmented
          value={prefs.showAiCompare ? "on" : "off"}
          onChange={(v) => update({ showAiCompare: v === "on" })}
          options={[
            { value: "off", label: "Off" },
            { value: "on", label: "On" },
          ]}
        />
      </Row>

      <Row
        label="Literature export"
        description="When exporting a grounded draft from Writing → Export."
      >
        <Segmented
          value={prefs.exportBundle}
          onChange={(v) => update({ exportBundle: v })}
          options={[
            { value: "md_bib", label: "MD + BibTeX" },
            { value: "md", label: "Markdown" },
          ]}
        />
      </Row>

      <Row
        label="Preferred citation style"
        description="Remembered preference for now — full CSL formatting ships later."
      >
        <Select
          value={prefs.citationStyle}
          onValueChange={(v) =>
            update({ citationStyle: v as ResearchPrefs["citationStyle"] })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="apa">APA</SelectItem>
            <SelectItem value="ieee">IEEE</SelectItem>
            <SelectItem value="chicago">Chicago</SelectItem>
            <SelectItem value="harvard">Harvard</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </Row>

      <Row
        label="After accepting evidence"
        description="Jump to the Writing desk so you can draft from what you just accepted."
      >
        <Segmented
          value={prefs.openWritingAfterAccept ? "writing" : "stay"}
          onChange={(v) => update({ openWritingAfterAccept: v === "writing" })}
          options={[
            { value: "stay", label: "Stay" },
            { value: "writing", label: "Open Writing" },
          ]}
        />
      </Row>
    </div>
  );
}
