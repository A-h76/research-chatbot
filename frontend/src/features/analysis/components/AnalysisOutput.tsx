import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { ChevronsDownUp, ChevronsUpDown, Copy, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";

export interface AnalysisOutputProps {
  analysis: string;
  sectionsCount?: number;
  onCopy?: () => void;
  onDownload?: () => void;
}

interface Section {
  heading: string;
  content: string;
  isMedical: boolean;
}

const MEDICAL_MIN = 17;
const MEDICAL_MAX = 30;

function parseSections(analysis: string): Section[] {
  return analysis
    .split(/(?=^##\s)/m)
    .map((part) => part.trim())
    .filter(Boolean)
    // A leading part that isn't itself a "## " heading is intro text ahead
    // of the first real section (or the whole string has no headings at
    // all) — discarded rather than rendered as a fake, numberless section.
    .filter((part) => /^##\s/.test(part))
    .map((part) => {
      const lines = part.split("\n");
      const heading = lines[0].replace(/^##\s*/, "").trim();
      const content = lines.slice(1).join("\n").trim();
      const match = heading.match(/^(\d+)\./);
      const sectionNumber = match ? parseInt(match[1], 10) : null;
      const isMedical = sectionNumber !== null && sectionNumber >= MEDICAL_MIN && sectionNumber <= MEDICAL_MAX;
      return { heading, content, isMedical };
    });
}

function triggerDownload(filename: string, content: string, mime: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function AnalysisOutput({ analysis, sectionsCount, onCopy, onDownload }: AnalysisOutputProps) {
  const sections = useMemo(() => parseSections(analysis ?? ""), [analysis]);
  const [openItems, setOpenItems] = useState<string[]>(() => sections.slice(0, 3).map((_, i) => String(i)));

  // A fresh analysis result (same component instance, e.g. re-running
  // "Analyze") should re-open the first 3 sections rather than keep
  // whatever was expanded for the previous result.
  useEffect(() => {
    setOpenItems(sections.slice(0, 3).map((_, i) => String(i)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis]);

  if (!analysis) return null;

  const allValues = sections.map((_, i) => String(i));
  const allOpen = sections.length > 0 && openItems.length === sections.length;

  function handleCopy() {
    navigator.clipboard.writeText(analysis).then(
      () => {
        toast.success("Copied to clipboard");
        onCopy?.();
      },
      () => toast.error("Could not copy to clipboard")
    );
  }

  function downloadMarkdown() {
    triggerDownload("analysis.md", analysis, "text/markdown");
    onDownload?.();
  }

  function downloadText() {
    triggerDownload("analysis.txt", analysis, "text/plain");
    onDownload?.();
  }

  function downloadJson() {
    const data = {
      domainDetected: null as string | null,
      sections: sections.map(({ heading, content, isMedical }) => ({ heading, content, isMedical })),
    };
    triggerDownload("analysis.json", JSON.stringify(data, null, 2), "application/json");
    onDownload?.();
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => setOpenItems(allOpen ? [] : allValues)}>
            {allOpen ? <ChevronsDownUp className="size-4" /> : <ChevronsUpDown className="size-4" />}
            {allOpen ? "Collapse all" : "Expand all"}
          </Button>
          {sectionsCount != null && (
            <span className="text-xs text-muted-foreground">{sectionsCount} sections</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={handleCopy}>
            <Copy className="size-4" />
            Copy
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button type="button" variant="outline" size="sm" />}>
              <Download className="size-4" />
              Download
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={downloadMarkdown}>Download as Markdown (.md)</DropdownMenuItem>
              <DropdownMenuItem onClick={downloadJson}>Download as JSON (.json)</DropdownMenuItem>
              <DropdownMenuItem onClick={downloadText}>Download as Plain Text (.txt)</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <Accordion value={openItems} onValueChange={setOpenItems} multiple>
        {sections.map((section, i) => (
          <AccordionItem
            key={i}
            value={String(i)}
            data-medical={section.isMedical || undefined}
            className={cn(section.isMedical && "border-l-2 border-l-rose-400 pl-3 dark:border-l-rose-500")}
          >
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                {section.isMedical && (
                  <span aria-label="Medical section" title="Medical section">
                    🩺
                  </span>
                )}
                {section.heading}
              </span>
            </AccordionTrigger>
            <AccordionContent>
              {section.content ? (
                <div className="prose-chat text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
                    {section.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm italic text-muted-foreground">No content available</p>
              )}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
