import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { useProjects } from "@/features/projects/useProjects";
import { ConversationItemMenu } from "./ConversationItemMenu";
import { cn } from "@/lib/utils";

export function ConversationList({ search }: { search: string }) {
  const { data: conversations = [], isLoading } = useConversations();
  const { data: projects = [] } = useProjects();
  const { currentProjectId } = useUI();
  const navigate = useNavigate();
  const params = useParams();
  const activeId = params.conversationId ? Number(params.conversationId) : null;

  const list = useMemo(() => {
    const q = search.trim().toLowerCase();
    return conversations
      .filter((c) => (currentProjectId ? c.project_id === currentProjectId : true))
      .filter((c) => (q ? c.title.toLowerCase().includes(q) : true));
  }, [conversations, currentProjectId, search]);

  if (isLoading) return null;

  if (!list.length) {
    return <p className="px-4 py-6 text-center text-sm text-muted-foreground">No chats yet</p>;
  }

  return (
    <div className="flex flex-col gap-0.5 px-2">
      <AnimatePresence initial={false}>
        {list.map((c) => {
          const proj = projects.find((p) => p.id === c.project_id);
          return (
            <motion.div
              key={c.id}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={() => navigate(`/c/${c.id}`)}
              className={cn(
                "group flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-sidebar-foreground hover:bg-sidebar-accent",
                activeId === c.id && "bg-sidebar-accent font-medium"
              )}
            >
              {!currentProjectId && proj && <span className="shrink-0">{proj.emoji}</span>}
              <span className="min-w-0 flex-1 truncate">{c.title}</span>
              <ConversationItemMenu convo={c} />
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
