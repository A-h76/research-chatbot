import { useState } from "react";
import { Brain } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { MemoryCard } from "../components/MemoryCard";
import { useDeleteMemory, useMemories, useUpdateMemory } from "../useMemories";
import { useProjects } from "@/features/projects/useProjects";
import { toast } from "@/components/common/Toast";
import type { Memory } from "@/types/api";

export function MemoryPage() {
  const { data: memories = [] } = useMemories();
  const { data: projects = [] } = useProjects();
  const updateMemory = useUpdateMemory();
  const deleteMemory = useDeleteMemory();
  const [toDelete, setToDelete] = useState<Memory | null>(null);

  return (
    <PageContainer
      title="Memory"
      description="What Dhund remembers about you. Memories appear as you chat."
    >
      {memories.length === 0 ? (
        <EmptyState
          icon={<Brain className="size-8" />}
          title="Nothing remembered yet"
          description="As you chat, durable facts (research topic, citation style, tools) are saved here."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {memories.map((m) => (
            <MemoryCard
              key={m.id}
              memory={m}
              project={projects.find((p) => p.id === m.project_id)}
              onUpdate={(body) => updateMemory.mutate({ id: m.id, body })}
              onDelete={() => setToDelete(m)}
            />
          ))}
        </div>
      )}
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Forget this memory?"
        entityName={toDelete?.fact?.slice(0, 100) || null}
        description="Dhund will stop using this fact in future research conversations."
        confirmLabel="Forget"
        cancelLabel="Keep"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteMemory.mutateAsync(toDelete.id);
          toast.success("Memory forgotten");
          setToDelete(null);
        }}
      />
    </PageContainer>
  );
}
