import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/common/Toast";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { cn } from "@/lib/utils";
import { collectionsApi, type LibraryCollection } from "../collectionsApi";
import { useLibraryCollections } from "../hooks/useLibraryCollections";

/** Lightweight Collections nav — counts, no boxed cards. */
export function CollectionsPanel({
  activeId,
  onSelect,
  totalPapers,
}: {
  activeId: number | null;
  onSelect: (id: number | null) => void;
  totalPapers?: number;
}) {
  const qc = useQueryClient();
  const { data: collections = [], isLoading } = useLibraryCollections();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [toDelete, setToDelete] = useState<LibraryCollection | null>(null);

  const invalidate = () => void qc.invalidateQueries({ queryKey: ["library", "collections"] });

  const createMut = useMutation({
    mutationFn: (n: string) => collectionsApi.create({ name: n }),
    onSuccess: (row) => {
      invalidate();
      setCreating(false);
      setName("");
      onSelect(row.id);
      toast.success(`Created “${row.name}”`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const renameMut = useMutation({
    mutationFn: ({ id, n }: { id: number; n: string }) => collectionsApi.update(id, { name: n }),
    onSuccess: () => {
      invalidate();
      setEditingId(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => collectionsApi.remove(id),
    onSuccess: (_d, id) => {
      invalidate();
      if (activeId === id) onSelect(null);
      toast.success("Collection removed — papers stay in your library");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const roots = collections.filter((c) => !c.parent_id);
  const childrenOf = (id: number) => collections.filter((c) => c.parent_id === id);

  function renderRow(c: LibraryCollection, depth = 0) {
    const active = activeId === c.id;
    if (editingId === c.id) {
      return (
        <div
          key={c.id}
          className="flex items-center gap-1 py-0.5"
          style={{ paddingLeft: 4 + depth * 12 }}
        >
          <Input
            value={editName}
            className="h-7 text-xs"
            autoFocus
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && editName.trim())
                renameMut.mutate({ id: c.id, n: editName.trim() });
              if (e.key === "Escape") setEditingId(null);
            }}
          />
          <Button
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={!editName.trim()}
            onClick={() => renameMut.mutate({ id: c.id, n: editName.trim() })}
          >
            Save
          </Button>
        </div>
      );
    }
    return (
      <div key={c.id}>
        <div
          className={cn(
            "group flex w-full items-center gap-1 text-left text-[13px] transition-colors",
            active
              ? "font-medium text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
          style={{ paddingLeft: 4 + depth * 12 }}
        >
          <button
            type="button"
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2 border-l-2 py-1.5 pl-2",
              active ? "border-primary" : "border-transparent",
            )}
            onClick={() => onSelect(c.id)}
          >
            <span className="truncate">{c.name}</span>
            <span className="ml-auto shrink-0 tabular-nums text-[11px] text-muted-foreground/80">
              {c.paper_count}
            </span>
          </button>
          <button
            type="button"
            className="hidden rounded p-0.5 opacity-0 hover:bg-muted group-hover:inline-flex group-hover:opacity-100"
            aria-label="Rename"
            onClick={() => {
              setEditingId(c.id);
              setEditName(c.name);
            }}
          >
            <Pencil className="size-3" />
          </button>
          <button
            type="button"
            className="hidden rounded p-0.5 text-destructive opacity-0 hover:bg-muted group-hover:inline-flex group-hover:opacity-100"
            aria-label="Delete collection"
            onClick={() => setToDelete(c)}
          >
            <Trash2 className="size-3" />
          </button>
        </div>
        {childrenOf(c.id).map((ch) => renderRow(ch, depth + 1))}
      </div>
    );
  }

  return (
    <aside className="w-full shrink-0 sm:w-48 lg:w-52">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Collections
        </h2>
        <button
          type="button"
          className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="New collection"
          onClick={() => setCreating(true)}
        >
          <FolderPlus className="size-3.5" />
        </button>
      </div>

      <button
        type="button"
        onClick={() => onSelect(null)}
        className={cn(
          "mb-1 flex w-full items-center gap-2 border-l-2 py-1.5 pl-2 text-left text-[13px]",
          activeId == null
            ? "border-primary font-medium text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        <span className="truncate">All papers</span>
        {totalPapers != null && (
          <span className="ml-auto shrink-0 tabular-nums text-[11px] text-muted-foreground/80">
            {totalPapers}
          </span>
        )}
      </button>

      {isLoading ? (
        <p className="pl-2 text-xs text-muted-foreground">Loading…</p>
      ) : (
        <div className="space-y-0.5">{roots.map((c) => renderRow(c))}</div>
      )}

      {creating && (
        <div className="mt-2 flex items-center gap-1">
          <Input
            value={name}
            placeholder="Collection name"
            className="h-7 text-xs"
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && name.trim()) createMut.mutate(name.trim());
              if (e.key === "Escape") setCreating(false);
            }}
          />
          <Button
            size="sm"
            className="h-7 px-2"
            disabled={!name.trim() || createMut.isPending}
            onClick={() => createMut.mutate(name.trim())}
          >
            Add
          </Button>
          <button
            type="button"
            className="p-1 text-muted-foreground"
            onClick={() => setCreating(false)}
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}

      {!isLoading && collections.length === 0 && !creating && (
        <p className="mt-3 pl-2 text-[11px] leading-relaxed text-muted-foreground">
          Organise papers into collections without copying them.
        </p>
      )}

      <ConfirmDialog
        open={toDelete != null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Remove collection?"
        entityName={toDelete?.name}
        description="Papers stay in your library. Only this folder organisation is removed."
        confirmLabel="Remove"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteMut.mutateAsync(toDelete.id);
          setToDelete(null);
        }}
      />
    </aside>
  );
}
