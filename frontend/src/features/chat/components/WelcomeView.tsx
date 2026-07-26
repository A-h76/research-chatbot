import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Library, FolderKanban } from "lucide-react";
import { Composer } from "./Composer";
import { SuggestionCards } from "./SuggestionCards";
import { ProjectInquiryRail } from "./ProjectInquiryRail";
import { useCreateConversation } from "../hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { useModels } from "@/features/models/useModels";
import { useProjects } from "@/features/projects/useProjects";
import { chatOutbox } from "../lib/outbox";
import { appendUserMessage } from "../lib/optimistic";
import type { ChatSettings, PendingFile } from "../types";
import type { Attachment, Me } from "@/types/api";

/** D6 — demoted global inquiry welcome (not a ChatGPT home). */
export function WelcomeView({ me }: { me: Me }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const createConversation = useCreateConversation();
  const { currentProjectId, defaultModel, defaultSearchMode } = useUI();
  const { data: modelsData } = useModels();
  const { data: projects = [] } = useProjects();
  const project = currentProjectId
    ? projects.find((p) => p.id === currentProjectId)
    : null;

  const initialModel = defaultModel || me.default_model || modelsData?.models[0] || me.default_model;
  const [settings, setSettings] = useState<ChatSettings>({
    model: initialModel,
    searchMode: defaultSearchMode,
    temperature: null,
    reasoningEffort: null,
    memoryEnabled: true,
  });

  const onSettingsChange = (partial: Partial<ChatSettings>) =>
    setSettings((s) => ({ ...s, ...partial }));

  const onSend = async (text: string, files: PendingFile[]) => {
    const conv = await createConversation.mutateAsync({
      model: settings.model,
      project_id: currentProjectId,
      temperature: settings.temperature,
      reasoning_effort: settings.reasoningEffort,
      memory_enabled: settings.memoryEnabled,
    });
    const attachments: Attachment[] = files.map((f) => ({
      id: f.id,
      name: f.name,
      kind: f.kind,
      mime: "",
    }));
    appendUserMessage(qc, conv.id, text, attachments);
    chatOutbox.set(conv.id, {
      text,
      attachmentIds: files.map((f) => f.id),
      searchMode: settings.searchMode,
    });
    navigate(`/c/${conv.id}`);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className={
          currentProjectId
            ? "grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(0,1fr)_17rem]"
            : "min-h-0 flex-1"
        }
      >
        <div className="flex min-h-0 min-w-0 flex-col items-center justify-center px-5 py-8">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mb-6 w-full max-w-xl text-center"
          >
            <h1 className="text-[20px] font-semibold tracking-tight">
              {project ? `Ask in ${project.name}` : "Ask Soro"}
            </h1>
            <p className="mt-1.5 text-[13px] text-muted-foreground">
              {project
                ? "Grounded in this project's papers. Prefer Paper Chat for evidence-linked answers."
                : "General inquiry. For evidence, entities, and GRADE — open a paper workspace."}
            </p>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-[12px]">
              <Link
                to="/library"
                className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-muted-foreground hover:text-foreground"
              >
                <Library className="size-3.5" /> Open Library
              </Link>
              {project ? (
                <Link
                  to={`/projects/${project.id}`}
                  className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-muted-foreground hover:text-foreground"
                >
                  <FolderKanban className="size-3.5" /> Project
                </Link>
              ) : (
                <Link
                  to="/projects"
                  className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-muted-foreground hover:text-foreground"
                >
                  <FolderKanban className="size-3.5" /> Projects
                </Link>
              )}
            </div>
          </motion.div>
          <div className="w-full max-w-xl">
            <Composer
              settings={settings}
              onSettingsChange={onSettingsChange}
              onSend={onSend}
              streaming={false}
              onStop={() => {}}
              conversationId={null}
              projectId={currentProjectId}
              autoFocus
            />
          </div>
          <div className="mt-5 w-full max-w-xl">
            <SuggestionCards onPick={(prompt) => onSend(prompt, [])} />
          </div>
        </div>
        {currentProjectId != null && (
          <aside className="hidden min-h-0 min-w-0 overflow-hidden border-l border-border p-3 lg:block">
            <ProjectInquiryRail projectId={currentProjectId} />
          </aside>
        )}
      </div>
    </div>
  );
}
