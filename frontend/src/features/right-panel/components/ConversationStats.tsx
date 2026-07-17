import type { Conversation } from "@/types/api";

export function ConversationStats({ conversation }: { conversation: Conversation }) {
  const userCount = conversation.messages.filter((m) => m.role === "user").length;
  const assistantCount = conversation.messages.filter((m) => m.role === "assistant").length;
  const words = conversation.messages.reduce((sum, m) => sum + m.content.trim().split(/\s+/).filter(Boolean).length, 0);

  const stats = [
    { label: "Messages", value: conversation.messages.length },
    { label: "You / AI", value: `${userCount} / ${assistantCount}` },
    { label: "Words", value: words.toLocaleString() },
    { label: "Model", value: conversation.model },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {stats.map((s) => (
        <div key={s.label} className="rounded-xl border border-border bg-card p-3">
          <p className="truncate text-sm font-medium">{s.value}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{s.label}</p>
        </div>
      ))}
    </div>
  );
}
