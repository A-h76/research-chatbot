import { useState } from "react";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Link2,
  MoreHorizontal,
  MessageSquareText,
  ChevronDown,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { HeadingLevel } from "../utils/writingFormatHelpers";

const HEADING_OPTIONS: { value: HeadingLevel; label: string }[] = [
  { value: "p", label: "Paragraph" },
  { value: "h1", label: "Title" },
  { value: "h2", label: "Heading 2" },
  { value: "h3", label: "Subheading" },
];

/** Theme palette — Word-style grid (row = theme, columns = accents). */
const THEME_COLORS: string[] = [
  "#000000",
  "#1f2937",
  "#4b5563",
  "#9ca3af",
  "#d1d5db",
  "#ffffff",
  "#7f1d1d",
  "#b91c1c",
  "#ef4444",
  "#fecaca",
  "#78350f",
  "#b45309",
  "#f59e0b",
  "#fde68a",
  "#14532d",
  "#15803d",
  "#22c55e",
  "#bbf7d0",
  "#0f6e6a",
  "#0d9488",
  "#2dd4bf",
  "#99f6e4",
  "#1e3a8a",
  "#1d4ed8",
  "#3b82f6",
  "#bfdbfe",
  "#4c1d95",
  "#6d28d9",
  "#8b5cf6",
  "#ddd6fe",
];

const STANDARD_COLORS: string[] = [
  "#c00000",
  "#ff0000",
  "#ffc000",
  "#ffff00",
  "#92d050",
  "#00b050",
  "#00b0f0",
  "#0070c0",
  "#002060",
  "#7030a0",
];

function ToolBtn({
  title,
  active,
  disabled,
  onClick,
  children,
}: {
  title: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-md text-[13px] transition-colors",
        active
          ? "bg-primary/15 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
        disabled && "opacity-40",
      )}
    >
      {children}
    </button>
  );
}

/** Word 2013–style font color: A + underline bar, split apply / palette. */
function FontColorControl({
  color,
  disabled,
  onColor,
}: {
  color: string;
  disabled?: boolean;
  onColor: (color: string) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className={cn(
        "inline-flex h-7 items-stretch overflow-hidden rounded-md",
        disabled && "opacity-40",
      )}
      data-testid="font-color-control"
    >
      <button
        type="button"
        disabled={disabled}
        title="Font color"
        aria-label="Apply font color"
        className="inline-flex min-w-7 flex-col items-center justify-center gap-0.5 px-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        onClick={() => onColor(color)}
      >
        <span className="text-[13px] font-semibold leading-none tracking-tight text-foreground">
          A
        </span>
        <span
          className="h-[3px] w-[14px] rounded-[1px]"
          style={{ backgroundColor: color }}
          aria-hidden
        />
      </button>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          disabled={disabled}
          title="More colors"
          aria-label="Choose font color"
          className="inline-flex w-4 items-center justify-center border-l border-border/50 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
        >
          <ChevronDown className="size-3" strokeWidth={2} />
        </PopoverTrigger>
        <PopoverContent align="start" className="w-[220px] gap-2 p-2.5" sideOffset={6}>
          <p className="px-0.5 text-[11px] font-medium text-muted-foreground">Theme colors</p>
          <div className="grid grid-cols-10 gap-0.5">
            {THEME_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                title={c}
                aria-label={`Color ${c}`}
                className={cn(
                  "size-4 rounded-[2px] border border-black/10 transition-transform hover:scale-110 hover:ring-1 hover:ring-foreground/30",
                  color.toLowerCase() === c.toLowerCase() && "ring-1 ring-foreground",
                )}
                style={{ backgroundColor: c }}
                onClick={() => {
                  onColor(c);
                  setOpen(false);
                }}
              />
            ))}
          </div>

          <p className="mt-1.5 px-0.5 text-[11px] font-medium text-muted-foreground">
            Standard colors
          </p>
          <div className="grid grid-cols-10 gap-0.5">
            {STANDARD_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                title={c}
                aria-label={`Color ${c}`}
                className={cn(
                  "size-4 rounded-[2px] border border-black/10 transition-transform hover:scale-110 hover:ring-1 hover:ring-foreground/30",
                  color.toLowerCase() === c.toLowerCase() && "ring-1 ring-foreground",
                )}
                style={{ backgroundColor: c }}
                onClick={() => {
                  onColor(c);
                  setOpen(false);
                }}
              />
            ))}
          </div>

          <button
            type="button"
            className="mt-1 flex w-full items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-[12px] text-foreground hover:bg-muted"
            onClick={() => {
              onColor("#000000");
              setOpen(false);
            }}
          >
            <span className="inline-flex size-4 items-center justify-center rounded-[2px] border border-border text-[10px] font-semibold">
              A
            </span>
            Automatic
          </button>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export function WritingManuscriptToolbar({
  heading,
  disabled,
  textColor = "#0f6e6a",
  onHeading,
  onBold,
  onItalic,
  onBullet,
  onNumbered,
  onLink,
  onColor,
  onMore,
}: {
  heading: HeadingLevel;
  disabled?: boolean;
  textColor?: string;
  onHeading: (level: HeadingLevel) => void;
  onBold: () => void;
  onItalic: () => void;
  onBullet: () => void;
  onNumbered: () => void;
  onLink: () => void;
  onColor: (color: string) => void;
  onMore?: () => void;
}) {
  return (
    <div
      className="flex shrink-0 flex-wrap items-center gap-0.5 border-b border-border/40 px-1 py-1"
      role="toolbar"
      aria-label="Manuscript formatting"
      data-testid="writing-manuscript-toolbar"
    >
      <select
        aria-label="Text style"
        disabled={disabled}
        value={heading}
        onChange={(e) => onHeading(e.target.value as HeadingLevel)}
        className="h-7 rounded-md border-0 bg-transparent px-1.5 text-[12px] font-medium text-foreground outline-none hover:bg-muted/50"
      >
        {HEADING_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <span className="mx-0.5 h-3.5 w-px bg-border/60" aria-hidden />

      <ToolBtn title="Bold" disabled={disabled} onClick={onBold}>
        <Bold className="size-3.5" strokeWidth={2.5} />
      </ToolBtn>
      <ToolBtn title="Italic" disabled={disabled} onClick={onItalic}>
        <Italic className="size-3.5" />
      </ToolBtn>

      <span className="mx-0.5 h-3.5 w-px bg-border/60" aria-hidden />

      <ToolBtn title="Bulleted list" disabled={disabled} onClick={onBullet}>
        <List className="size-3.5" />
      </ToolBtn>
      <ToolBtn title="Numbered list" disabled={disabled} onClick={onNumbered}>
        <ListOrdered className="size-3.5" />
      </ToolBtn>

      <span className="mx-0.5 h-3.5 w-px bg-border/60" aria-hidden />

      <ToolBtn title="Link" disabled={disabled} onClick={onLink}>
        <Link2 className="size-3.5" />
      </ToolBtn>

      <FontColorControl color={textColor} disabled={disabled} onColor={onColor} />

      <div className="ml-auto flex items-center gap-0.5">
        <ToolBtn title="Comment" disabled={disabled} onClick={() => onMore?.()}>
          <MessageSquareText className="size-3.5" />
        </ToolBtn>
        <ToolBtn title="More" disabled={disabled} onClick={() => onMore?.()}>
          <MoreHorizontal className="size-3.5" />
        </ToolBtn>
      </div>
    </div>
  );
}
