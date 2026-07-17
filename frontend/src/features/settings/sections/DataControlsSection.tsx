import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Download, Trash2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { toast } from "@/components/common/Toast";
import { queryKeys } from "@/lib/queryKeys";
import { downloadExport, settingsApi, type ExportFormat } from "../api";

const FORMATS: { value: ExportFormat; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "Word" },
  { value: "md", label: "Markdown" },
  { value: "txt", label: "Text" },
  { value: "json", label: "JSON" },
];

function Card({ title, description, children, danger }: {
  title: string; description: string; children: React.ReactNode; danger?: boolean;
}) {
  return (
    <div className={danger
      ? "rounded-xl border border-destructive/40 bg-destructive/5 p-5"
      : "rounded-xl border border-border bg-muted/40 p-5"}>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-0.5 mb-3 text-sm text-muted-foreground">{description}</p>
      {children}
    </div>
  );
}

export function DataControlsSection() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [ack, setAck] = useState("");
  const [busy, setBusy] = useState(false);

  const clearAllChats = async () => {
    try {
      const res = await settingsApi.deleteAllChats();
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
      toast.success(`Deleted ${res.deleted} chat${res.deleted === 1 ? "" : "s"}`);
      navigate("/");
    } catch {
      toast.error("Could not delete chats");
    }
  };

  const deleteAccount = async () => {
    setBusy(true);
    try {
      await settingsApi.deleteAccount();
      window.location.href = "/login";
    } catch {
      toast.error("Could not delete account");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card title="Export your data"
            description="Download all your conversations, attachments metadata, and citations.">
        <div className="flex flex-wrap gap-2">
          {FORMATS.map((f) => (
            <Button key={f.value} variant="outline" size="sm"
                    onClick={() => { downloadExport(f.value); toast.success(`Preparing ${f.label} export…`); }}>
              <Download className="size-4" /> {f.label}
            </Button>
          ))}
        </div>
      </Card>

      <Card title="Delete all chats"
            description="Permanently remove every conversation and its attachments. Projects, citations, and memories are kept.">
        <Button variant="destructive" onClick={() => setConfirmClear(true)}>
          <Trash2 className="size-4" /> Delete all chats
        </Button>
      </Card>

      <Card danger title="Delete account"
            description="Permanently erase your account and all associated data — chats, files, memories, citations, and projects. This cannot be undone.">
        <Button variant="destructive" onClick={() => { setAck(""); setConfirmDelete(true); }}>
          <AlertTriangle className="size-4" /> Delete my account
        </Button>
      </Card>

      <ConfirmDialog
        open={confirmClear}
        onOpenChange={setConfirmClear}
        title="Delete all chats?"
        description="Every conversation and its attachments will be permanently removed. This can't be undone."
        confirmLabel="Delete all"
        destructive
        onConfirm={clearAllChats}
      />

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete your account?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes your account and all data. Type <b>DELETE</b> to confirm.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            autoFocus
            value={ack}
            onChange={(e) => setAck(e.target.value)}
            placeholder="DELETE"
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={ack !== "DELETE" || busy}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/80"
              onClick={(e) => { e.preventDefault(); deleteAccount(); }}
            >
              Delete account
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
