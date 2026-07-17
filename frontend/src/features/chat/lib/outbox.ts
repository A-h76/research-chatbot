import type { SearchMode } from "@/types/api";

// Carries the first message of a brand-new conversation across the
// create-conversation → navigate(/c/:id) → ConversationView boundary, so the
// stream can start once the view for the new id mounts.
export interface OutboxItem {
  text: string;
  attachmentIds: number[];
  searchMode: SearchMode;
}

const outbox = new Map<number, OutboxItem>();

export const chatOutbox = {
  set: (id: number, item: OutboxItem) => outbox.set(id, item),
  take: (id: number): OutboxItem | undefined => {
    const item = outbox.get(id);
    if (item) outbox.delete(id);
    return item;
  },
};
