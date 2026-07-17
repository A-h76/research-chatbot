import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Composer } from "./Composer";
import { SuggestionCards } from "./SuggestionCards";
import { useCreateConversation } from "../hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { useModels } from "@/features/models/useModels";
import { chatOutbox } from "../lib/outbox";
import { appendUserMessage } from "../lib/optimistic";
import type { ChatSettings, PendingFile } from "../types";
import type { Attachment, Me } from "@/types/api";

export function WelcomeView({ me }: { me: Me }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const createConversation = useCreateConversation();
  const { currentProjectId, defaultModel, defaultSearchMode } = useUI();
  const { data: modelsData } = useModels();

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
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-5">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8 text-center"
        >
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            New conversation
          </h1>
          <p className="mt-2 text-muted-foreground">Ask anything, or attach a paper to start researching.</p>
        </motion.div>
        <div className="w-full">
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
        <div className="mt-6 w-full">
          <SuggestionCards onPick={(prompt) => onSend(prompt, [])} />
        </div>
      </div>
    </div>
  );
}
