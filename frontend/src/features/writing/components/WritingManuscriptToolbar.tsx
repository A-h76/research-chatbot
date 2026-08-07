import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Link2,
  MoreHorizontal,
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

      <label className="ml-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
        <span className="sr-only">Font color</span>
        <input
          type="color"
          disabled={disabled}
          defaultValue="#0f6e6a"
          title="Font color"
          aria-label="Font color"
          className="size-6 cursor-pointer rounded border-0 bg-transparent p-0.5"
          onChange={(e) => onColor(e.target.value)}
        />
      </label>

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
