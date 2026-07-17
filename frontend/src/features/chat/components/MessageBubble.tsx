import { FileText } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { SourcesChips } from "./SourcesChips";
import { MessageActions } from "./MessageActions";
import type { Attachment, Message, Source } from "@/types/api";

function AttachmentChips({ attachments }: { attachments: Attachment[] }) {
  if (!attachments.length) return null;
  return (
    <div className="mb-1.5 flex flex-wrap justify-end gap-1.5">
      {attachments.map((a) =>
        a.kind === "image" ? (
          <img
            key={a.id}
            src={`/api/files/${a.id}/raw`}
            alt={a.name}
            className="size-28 rounded-xl border border-border object-cover"
          />
        ) : (
          <div
            key={a.id}
            className="flex max-w-[230px] items-center gap-1.5 rounded-xl border border-border bg-card px-2.5 py-1.5 text-xs"
          >
            <FileText className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate">{a.name}</span>
          </div>
        )
      )}
    </div>
  );
}

export function UserMessage({ message }: { message: Message }) {
  return (
    <div className="flex flex-col items-end gap-1.5">
      <AttachmentChips attachments={message.attachments} />
      <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-user-bubble px-4 py-2.5 text-[0.95rem] text-user-bubble-foreground">
        {message.content}
      </div>
    </div>
  );
}

export function AssistantMessage({
  content,
  sources,
  onRegenerate,
  streaming,
}: {
  content: string;
  sources?: Source[];
  onRegenerate?: () => void;
  streaming?: boolean;
}) {
  return (
    <div className="flex gap-3.5">
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border border-border text-sm">
        ✦
      </div>
      <div className="min-w-0 flex-1">
        <MarkdownRenderer content={content} />
        {streaming && (
          <span className="ml-0.5 inline-block h-4 w-[3px] translate-y-0.5 animate-pulse rounded-full bg-foreground align-middle" />
        )}
        {!streaming && sources && <SourcesChips sources={sources} />}
        {!streaming && <MessageActions content={content} onRegenerate={onRegenerate} />}
      </div>
    </div>
  );
}
