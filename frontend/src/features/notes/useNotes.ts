import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { notesApi, type NoteInput, type NoteListParams } from "./api";
import type { Note } from "@/types/api";

export function useNotes(params: NoteListParams = {}) {
  return useQuery({
    queryKey: [...queryKeys.notes, params],
    queryFn:  () => notesApi.list(params),
  });
}

export function useNote(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.note(id) : ["notes", "none"],
    queryFn:  () => notesApi.get(id!),
    enabled:  id !== null,
  });
}

export function useCreateNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NoteInput) => notesApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notes });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<NoteInput> }) =>
      notesApi.update(id, body),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: queryKeys.notes });
      qc.setQueryData<Note>(queryKeys.note(updated.id), updated);
    },
  });
}

export function useDeleteNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notes });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
