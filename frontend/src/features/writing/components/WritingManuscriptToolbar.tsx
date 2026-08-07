import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Link2,
  MoreHorizontal,
  Undo2,
  Redo2,
  MessageSquareText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { HeadingLevel } from "../utils/writingFormatHelpers";

const HEADING_OPTIONS: { value: HeadingLevel; label: string }[] = [
  { value: "p", label: "Paragraph" },
  { value: "h1", label: "Title" },
  { value: "h2", label: "Heading 2" },
  { value: "h3", label: "Subheading" },
];

const COLORS = [
  { value: "#1a1a1a", label: "Default" },
  { value: "#0f6e6a", label: "Teal" },
  { value: "#1d4ed8", label: "Blue" },
  { value: "#b45309", label: "Amber" },
  { value: "#b91c1c", label: "Red" },
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

export function WritingManuscriptToolbar({
  heading,
  disabled,
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
      className="flex shrink-0 flex-wrap items-center gap-0.5 border-b border-border bg-background px-2 py-1.5"
      role="toolbar"
      aria-label="Manuscript formatting"
      data-testid="writing-manuscript-toolbar"
    >
      <select
        aria-label="Text style"
        disabled={disabled}
        value={heading}
        onChange={(e) => onHeading(e.target.value as HeadingLevel)}
        className="h-7 rounded-md border border-border bg-card px-2 text-[12px] font-medium text-foreground"
      >
        {HEADING_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <span className="mx-1 h-4 w-px bg-border" aria-hidden />

      <ToolBtn title="Bold" disabled={disabled} onClick={onBold}>
        <Bold className="size-3.5" strokeWidth={2.5} />
      </ToolBtn>
      <ToolBtn title="Italic" disabled={disabled} onClick={onItalic}>
        <Italic className="size-3.5" />
      </ToolBtn>

      <span className="mx-1 h-4 w-px bg-border" aria-hidden />

      <ToolBtn title="Bulleted list" disabled={disabled} onClick={onBullet}>
        <List className="size-3.5" />
      </ToolBtn>
      <ToolBtn title="Numbered list" disabled={disabled} onClick={onNumbered}>
        <ListOrdered className="size-3.5" />
      </ToolBtn>

      <span className="mx-1 h-4 w-px bg-border" aria-hidden />

      <ToolBtn title="Link" disabled={disabled} onClick={onLink}>
        <Link2 className="size-3.5" />
      </ToolBtn>
      <ToolBtn title="Comment" disabled={disabled} onClick={() => onMore?.()}>
        <MessageSquareText className="size-3.5" />
      </ToolBtn>

      <label className="ml-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
        <span className="sr-only">Font color</span>
        <input
          type="color"
          disabled={disabled}
          defaultValue="#0f6e6a"
          title="Font color"
          aria-label="Font color"
          className="size-7 cursor-pointer rounded border border-border bg-card p-0.5"
          onChange={(e) => onColor(e.target.value)}
        />
      </label>
      <select
        aria-label="Text color preset"
        disabled={disabled}
        defaultValue=""
        className="h-7 max-w-[5.5rem] rounded-md border border-border bg-card px-1 text-[11px] text-foreground"
        onChange={(e) => {
          if (e.target.value) onColor(e.target.value);
        }}
      >
        <option value="" disabled>
          Color
        </option>
        {COLORS.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>

      <span className="mx-1 hidden h-4 w-px bg-border sm:block" aria-hidden />

      <ToolBtn title="Undo" disabled onClick={() => undefined}>
        <Undo2 className="size-3.5" />
      </ToolBtn>
      <ToolBtn title="Redo" disabled onClick={() => undefined}>
        <Redo2 className="size-3.5" />
      </ToolBtn>

      <div className="ml-auto">
        <ToolBtn title="More" disabled={disabled} onClick={() => onMore?.()}>
          <MoreHorizontal className="size-3.5" />
        </ToolBtn>
      </div>
    </div>
  );
}
