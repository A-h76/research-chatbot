import { useEffect, useRef, useState } from "react";
import { Plus, ArrowUp, Square, FileUp, FolderUp } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ComposerAttachments } from "./ComposerAttachments";
import { ModelPickerPopover } from "./ModelPickerPopover";
import { SearchModePicker } from "./SearchModePicker";
import { TemperatureControl } from "./TemperatureControl";
import { ReasoningEffortControl } from "./ReasoningEffortControl";
import { MemoryToggle } from "./MemoryToggle";
import { VoiceInputButton } from "./VoiceInputButton";
import { filesApi, isDocumentUpload } from "@/features/files/api";
import type { BulkBatchStatus } from "@/features/files/api";
import { BulkUploadProgress } from "@/features/files/components/BulkUploadProgress";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "@/components/common/Toast";
import { supportsReasoningEffort, supportsTemperature } from "@/lib/modelCapabilities";
import type { ChatSettings, PendingFile } from "../types";
import type { UserFile } from "@/types/api";
import { cn } from "@/lib/utils";

let tempIdCounter = -1;

// /api/documents/upload only enqueues the job — poll the (session-authed,
// already-existing) file record until the worker finishes it.
// ponytail: fixed interval/attempt ceiling, not backoff — fine at this
// volume; revisit if uploads start regularly exceeding the 60s cap.
async function pollForReady(
  id: number,
  { intervalMs = 2000, maxAttempts = 30 } = {}
): Promise<UserFile> {
  for (let i = 0; i < maxAttempts; i++) {
    const uf = await filesApi.get(id);
    if (uf.meta_status === "done" || uf.meta_status === "failed") return uf;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Processing timed out");
}

export function Composer({
  settings,
  onSettingsChange,
  onSend,
  streaming,
  onStop,
  conversationId,
  projectId,
  autoFocus,
}: {
  settings: ChatSettings;
  onSettingsChange: (partial: Partial<ChatSettings>) => void;
  onSend: (text: string, attachments: PendingFile[]) => void;
  streaming: boolean;
  onStop: () => void;
  conversationId?: number | null;
  projectId?: number | null;
  autoFocus?: boolean;
}) {
  const [text, setText] = useState("");
  const [pending, setPending] = useState<PendingFile[]>([]);
  // Set once a document batch is accepted (POST /api/uploads/bulk 201);
  // <BulkUploadProgress> below owns polling it from there, replacing the
  // old one-poll-per-file approach.
  const [activeBatch, setActiveBatch] = useState<{ batchId: string; jobFileIds: number[] } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const uploading = pending.some((f) => f.uploading);
  const canSend = !uploading && (text.trim().length > 0 || pending.length > 0);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  const autoGrow = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  useEffect(autoGrow, [text]);

  const IGNORE_PATH = /(^|\/)(node_modules|\.git|\.next|dist|build|\.venv|venv|__pycache__|\.idea|\.vscode|\.DS_Store)(\/|$)/;
  const MAX_FOLDER_FILES = 40;

  const handleFiles = async (fileList: FileList, fromFolder = false) => {
    let files = Array.from(fileList);
    if (fromFolder) {
      files = files.filter((f) => {
        const rel = (f as { webkitRelativePath?: string }).webkitRelativePath || f.name;
        return !IGNORE_PATH.test(rel) && !f.name.startsWith(".");
      });
      if (files.length === 0) {
        toast.error("No uploadable files found in that folder.");
        return;
      }
      if (files.length > MAX_FOLDER_FILES) {
        toast.info(`Folder has ${files.length} files — uploading the first ${MAX_FOLDER_FILES}.`);
        files = files.slice(0, MAX_FOLDER_FILES);
      }
    }
    // Documents (pdf/epub/docx/txt) go through the bulk endpoint — one
    // request for all of them instead of one /api/documents/upload call
    // per file. Everything else (images, mainly) keeps the original
    // one-request-per-file path; the bulk route doesn't accept images.
    const documentFiles = files.filter((f) => isDocumentUpload(f.name));
    const otherFiles = files.filter((f) => !isDocumentUpload(f.name));

    for (const file of otherFiles) {
      const tempId = tempIdCounter--;
      let currentId = tempId; // reassigned once the real id is known, so the catch below can still find the item
      setPending((p) => [...p, { id: tempId, name: file.name, kind: "document", uploading: true, size: file.size }]);
      try {
        const outcome = await filesApi.upload(file, conversationId, projectId);
        if (!outcome.async) {
          const res = outcome.result;
          setPending((p) =>
            p.map((f) => (f.id === tempId ? { id: res.id, name: res.name, kind: res.kind } : f))
          );
          qc.invalidateQueries({ queryKey: queryKeys.files });
          if (res.note === "scanned_pdf") {
            toast.info(`${res.name}: no text layer — it'll be read as page images.`);
          } else if (res.note) {
            toast.warning(`${res.name}: ${res.note}.`);
          } else {
            toast.success(
              res.kind === "document" ? `Indexed ${res.name} (${res.chunks} sections)` : `Attached ${res.name}`
            );
          }
          continue;
        }

        // Defensive only — isDocumentUpload() routes actual documents to
        // the bulk branch below, so upload() shouldn't return the async
        // shape here in practice.
        const { document_id } = outcome.result;
        currentId = document_id;
        setPending((p) =>
          p.map((f) => (f.id === tempId ? { id: document_id, name: file.name, kind: "document", uploading: true } : f))
        );
        const uf = await pollForReady(document_id);
        qc.invalidateQueries({ queryKey: queryKeys.files });
        if (uf.meta_status === "failed") {
          setPending((p) => p.filter((f) => f.id !== document_id));
          toast.error(`${file.name}: processing failed`);
        } else {
          setPending((p) => p.map((f) => (f.id === document_id ? { ...f, uploading: false } : f)));
          toast.success(`Indexed ${uf.name} (${uf.chunks} sections)`);
        }
      } catch (err) {
        setPending((p) => p.filter((f) => f.id !== currentId));
        toast.error(err instanceof Error ? err.message : "Upload failed");
      }
    }

    if (documentFiles.length > 0) {
      const tempIds = documentFiles.map(() => tempIdCounter--);
      setPending((p) => [
        ...p,
        ...documentFiles.map((file, i) => ({
          id: tempIds[i], name: file.name, kind: "document" as const, uploading: true, size: file.size,
        })),
      ]);
      try {
        // One POST for the whole batch — jobs[] comes back in the same
        // order the files were sent, one job per file. From here,
        // <BulkUploadProgress> (rendered below, keyed on activeBatch)
        // polls the batch status endpoint and reports back via
        // onComplete/onError — no per-file polling loop here anymore.
        const { batch_id, jobs } = await filesApi.uploadFiles(documentFiles);
        setPending((p) =>
          p.map((f) => {
            const i = tempIds.indexOf(f.id);
            return i === -1
              ? f
              : { id: jobs[i].file_id, name: jobs[i].filename, kind: "document" as const, uploading: true, size: f.size };
          })
        );
        setActiveBatch({ batchId: String(batch_id), jobFileIds: jobs.map((j) => j.file_id) });
        toast.info(`Uploading ${documentFiles.length} file${documentFiles.length === 1 ? "" : "s"}…`);
      } catch (err) {
        // Whole-batch rejection (validation/quota/storage) — the bulk
        // route is all-or-nothing, so no file in this drop was stored;
        // clear all of its pending rows, not just one.
        setPending((p) => p.filter((f) => !tempIds.includes(f.id)));
        toast.error(err instanceof Error ? err.message : "Upload failed");
      }
    }
  };

  const handleBatchComplete = (data: BulkBatchStatus) => {
    qc.invalidateQueries({ queryKey: queryKeys.files });
    const failed = data.jobs.filter((j) => j.status === "failed");
    const ok = data.jobs.filter((j) => j.status !== "failed");

    setPending((p) =>
      p
        .filter((f) => !failed.some((j) => j.file_id === f.id))
        .map((f) => (ok.some((j) => j.file_id === f.id) ? { ...f, uploading: false } : f))
    );

    if (ok.length > 0) toast.success(`Indexed ${ok.length} file${ok.length === 1 ? "" : "s"}`);
    for (const j of failed) toast.error(`${j.filename}: processing failed`);

    setActiveBatch(null);
  };

  const handleBatchError = (message: string) => {
    if (activeBatch) {
      setPending((p) => p.filter((f) => !activeBatch.jobFileIds.includes(f.id)));
    }
    toast.error(message);
    setActiveBatch(null);
  };

  const submit = () => {
    if (streaming) {
      onStop();
      return;
    }
    if (!canSend) return;
    onSend(text.trim(), pending);
    setText("");
    setPending([]);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const showTemp = supportsTemperature(settings.model);
  const showReasoning = supportsReasoningEffort(settings.model);

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="rounded-3xl border border-border bg-card p-2.5 shadow-sm transition-shadow focus-within:shadow-md">
        <ComposerAttachments files={pending} onRemove={(id) => setPending((p) => p.filter((f) => f.id !== id))} />
        {activeBatch && (
          <div className="mb-2">
            <BulkUploadProgress
              batchId={activeBatch.batchId}
              onComplete={handleBatchComplete}
              onError={handleBatchError}
            />
          </div>
        )}
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Message Personal AI…"
          className="max-h-50 w-full resize-none bg-transparent px-2.5 py-1.5 text-[0.95rem] outline-none placeholder:text-muted-foreground"
        />
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <input
            ref={folderInputRef}
            type="file"
            className="hidden"
            {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files, true);
              e.target.value = "";
            }}
          />
          <DropdownMenu>
            <DropdownMenuTrigger
              title="Attach files or a folder"
              className="inline-flex size-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-hover hover:text-foreground"
            >
              <Plus className="size-4.5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-52">
              <DropdownMenuItem onClick={() => fileInputRef.current?.click()}>
                <FileUp className="size-4" /> Upload files
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => folderInputRef.current?.click()}>
                <FolderUp className="size-4" /> Upload folder
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <ModelPickerPopover value={settings.model} onChange={(m) => onSettingsChange({ model: m })} />
          <SearchModePicker value={settings.searchMode} onChange={(m) => onSettingsChange({ searchMode: m })} />
          {showReasoning && (
            <ReasoningEffortControl
              value={settings.reasoningEffort}
              onChange={(v) => onSettingsChange({ reasoningEffort: v })}
            />
          )}
          {showTemp && (
            <TemperatureControl
              value={settings.temperature}
              onChange={(v) => onSettingsChange({ temperature: v })}
            />
          )}
          <MemoryToggle enabled={settings.memoryEnabled} onChange={(v) => onSettingsChange({ memoryEnabled: v })} />
          <div className="ml-auto flex items-center gap-1">
            <VoiceInputButton onTranscript={(t) => setText((prev) => (prev ? prev + " " + t : t))} />
            <button
              type="button"
              onClick={submit}
              disabled={!streaming && !canSend}
              className={cn(
                "inline-flex size-9 items-center justify-center rounded-full transition-colors disabled:opacity-30",
                streaming
                  ? "bg-muted text-foreground hover:bg-muted/80"
                  : "bg-foreground text-background hover:bg-foreground/90"
              )}
              title={streaming ? "Stop" : "Send"}
            >
              {streaming ? <Square className="size-4 fill-current" /> : <ArrowUp className="size-4.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
