import { useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, FileText, ExternalLink, Brain } from "lucide-react";
import { ConversationStats } from "./ConversationStats";
import { useConversation } from "@/features/chat/hooks/useConversation";
import { useAllFiles } from "@/features/files/useFiles";
import { useMemories } from "@/features/memory/useMemories";
import { useUI } from "@/context/UIContext";

function PanelSection({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
        {count !== undefined && count > 0 && (
          <span className="rounded-full bg-muted px-1.5 text-xs text-muted-foreground">{count}</span>
        )}
      </div>
      {children}
    </div>
  );
}

export function RightPanel() {
  const { conversationId } = useParams();
  const id = conversationId ? Number(conversationId) : null;
  const { rightPanelOpen, setRightPanelOpen } = useUI();
  const { data: conversation } = useConversation(id);
  const { data: files = [] } = useAllFiles();
  const { data: memories = [] } = useMemories();

  const open = rightPanelOpen && !!id && !!conversation;

  const convFiles = files.filter((f) => f.conversation_id === id || (conversation?.project_id && f.project_id === conversation.project_id));
  const sources = conversation
    ? conversation.messages.flatMap((m) => m.sources).filter((s, i, arr) => s.url && arr.findIndex((x) => x.url === s.url) === i)
    : [];
  const scopedMemories = memories.filter(
    (m) => m.project_id === null || (conversation?.project_id && m.project_id === conversation.project_id)
  );

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.22, ease: "easeInOut" }}
          className="hidden shrink-0 overflow-hidden border-l border-border bg-sidebar lg:block"
        >
          <div className="scrollbar-thin h-full w-80 overflow-y-auto p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Context</h2>
              <button
                onClick={() => setRightPanelOpen(false)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="flex flex-col gap-5">
              <PanelSection title="Conversation stats">
                {conversation && <ConversationStats conversation={conversation} />}
              </PanelSection>

              <PanelSection title="Files" count={convFiles.length}>
                {convFiles.length ? (
                  <div className="flex flex-col gap-1.5">
                    {convFiles.map((f) => (
                      <div key={f.id} className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs">
                        <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                        <span className="truncate">{f.name}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No files in this chat.</p>
                )}
              </PanelSection>

              <PanelSection title="Retrieved sources" count={sources.length}>
                {sources.length ? (
                  <div className="flex flex-col gap-1.5">
                    {sources.slice(0, 10).map((s, i) => (
                      <a
                        key={i}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="size-3.5 shrink-0" />
                        <span className="truncate">{s.title || s.url}</span>
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No web sources used yet.</p>
                )}
              </PanelSection>

              <PanelSection title="Memory used" count={scopedMemories.length}>
                {scopedMemories.length ? (
                  <div className="flex flex-col gap-1.5">
                    {scopedMemories.slice(0, 8).map((m) => (
                      <div key={m.id} className="flex items-start gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs">
                        <Brain className="mt-0.5 size-3.5 shrink-0 text-primary" />
                        <span className="line-clamp-2">{m.fact}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No memories in scope.</p>
                )}
              </PanelSection>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
