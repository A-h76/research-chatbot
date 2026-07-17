import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BookOpen, BookMarked, CheckCircle2, Library,
  MessageSquare, Quote, FolderKanban, FileText,
  ArrowRight, Loader2, Tag, Clock,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useMe } from "@/features/profile/useMe";
import { useUI } from "@/context/UIContext";
import { useDashboard } from "./useDashboard";
import { cn } from "@/lib/utils";
import type { DashboardPaperBrief, DashboardChat, DashboardProject } from "./api";

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({
  icon,
  label,
  value,
  sub,
  color,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  sub?: string;
  color?: string;
  onClick?: () => void;
}) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={onClick ? { y: -2 } : undefined}
      transition={{ duration: 0.15 }}
      className={cn(
        "flex flex-col gap-2 rounded-2xl border border-border bg-card p-4 text-left shadow-sm",
        onClick && "cursor-pointer hover:border-primary/30 hover:shadow-md transition-all",
        !onClick && "cursor-default",
      )}
    >
      <div className={cn("flex size-9 items-center justify-center rounded-xl", color ?? "bg-muted")}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        {sub && <p className="mt-0.5 text-[10px] text-muted-foreground/70">{sub}</p>}
      </div>
    </motion.button>
  );
}

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({
  icon,
  title,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-primary">{icon}</span>
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
        >
          {action.label} <ArrowRight className="size-3" />
        </button>
      )}
    </div>
  );
}

// ── Paper row ────────────────────────────────────────────────────────────────
const RS_ICON = {
  read:    <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />,
  reading: <BookMarked   className="size-3.5 text-amber-600  dark:text-amber-400"   />,
  unread:  <BookOpen     className="size-3.5 text-muted-foreground"                 />,
};

function PaperRow({ paper, onClick }: { paper: DashboardPaperBrief; onClick: () => void }) {
  const title = paper.title || paper.name;
  const rs = (paper.reading_status ?? "unread") as "read" | "reading" | "unread";
  const isProcessing = paper.meta_status === "pending" || paper.meta_status === "running";

  return (
    <button
      onClick={onClick}
      className="flex w-full items-start gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-muted/60"
    >
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft">
        <FileText className="size-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium leading-snug" title={title}>{title}</p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {[paper.authors?.split(";")[0]?.trim(), paper.year].filter(Boolean).join(" · ") || "No metadata yet"}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
        {isProcessing && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
        {RS_ICON[rs]}
      </div>
    </button>
  );
}

// ── Chat row ─────────────────────────────────────────────────────────────────
function ChatRow({ chat, onClick }: { chat: DashboardChat; onClick: () => void }) {
  const isPaperChat = chat.file_id !== null;
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-muted/60"
    >
      <div className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg",
        isPaperChat ? "bg-accent-soft" : "bg-muted",
      )}>
        <MessageSquare className={cn("size-4", isPaperChat ? "text-primary" : "text-muted-foreground")} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{chat.title}</p>
        {isPaperChat && (
          <p className="text-[10px] text-primary/80">Paper chat</p>
        )}
      </div>
      <Clock className="size-3.5 shrink-0 text-muted-foreground" />
    </button>
  );
}

// ── Project card ─────────────────────────────────────────────────────────────
function ProjectCard({ project, onClick }: { project: DashboardProject; onClick: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.12 }}
      className="flex flex-col gap-2.5 rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition-all hover:border-primary/30"
    >
      <span className="text-2xl leading-none">{project.emoji}</span>
      <div>
        <p className="text-sm font-medium leading-snug">{project.name}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {project.paper_count} paper{project.paper_count !== 1 ? "s" : ""} ·{" "}
          {project.chat_count} chat{project.chat_count !== 1 ? "s" : ""}
        </p>
      </div>
    </motion.button>
  );
}

// ── Reading progress bar ─────────────────────────────────────────────────────
function ReadingProgress({
  unread, reading, read, total,
}: {
  unread: number; reading: number; read: number; total: number;
}) {
  if (total === 0) return null;
  const pct = (n: number) => Math.round((n / total) * 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Reading progress</span>
        <span>{pct(read)}% read</span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="bg-emerald-500 transition-all"
          style={{ width: `${pct(read)}%` }}
          title={`${read} read`}
        />
        <div
          className="bg-amber-400 transition-all"
          style={{ width: `${pct(reading)}%` }}
          title={`${reading} reading`}
        />
      </div>
      <div className="flex gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-emerald-500" /> {read} read
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-amber-400" /> {reading} reading
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-muted-foreground/40" /> {unread} unread
        </span>
      </div>
    </div>
  );
}

// ── Skeleton loader ──────────────────────────────────────────────────────────
function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="h-4 w-32" />
            {Array.from({ length: 3 }).map((_, j) => (
              <Skeleton key={j} className="h-12 rounded-xl" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export function DashboardPage() {
  const navigate = useNavigate();
  const { data: me } = useMe();
  const { setCurrentProjectId } = useUI();
  const { data, isLoading } = useDashboard();

  const firstName = me?.name.split(" ")[0] ?? "";

  function openProject(id: number) {
    setCurrentProjectId(id);
    navigate("/");
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8">

        {/* ── Greeting ── */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mb-8"
        >
          <h1 className="text-2xl font-semibold tracking-tight">
            {firstName ? `Welcome back, ${firstName}` : "Research Dashboard"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Pick up where you left off.
          </p>
        </motion.div>

        {isLoading ? (
          <DashboardSkeleton />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Could not load dashboard.</p>
        ) : (
          <div className="space-y-10">

            {/* ── Stat grid ── */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard
                icon={<Library className="size-5 text-primary" />}
                color="bg-accent-soft"
                label="Papers"
                value={data.library.total_papers}
                onClick={() => navigate("/files")}
              />
              <StatCard
                icon={<BookMarked className="size-5 text-amber-600 dark:text-amber-400" />}
                color="bg-amber-50 dark:bg-amber-950/40"
                label="Reading"
                value={data.library.reading}
                sub={data.library.total_papers > 0
                  ? `${Math.round((data.library.reading / data.library.total_papers) * 100)}% of library`
                  : undefined}
                onClick={() => navigate("/files?reading_status=reading")}
              />
              <StatCard
                icon={<MessageSquare className="size-5 text-primary" />}
                color="bg-accent-soft"
                label="Chats"
                value={data.recent_chats.length > 0
                  ? `${data.recent_chats.length}+`
                  : 0}
                onClick={() => navigate("/")}
              />
              <StatCard
                icon={<Quote className="size-5 text-primary" />}
                color="bg-accent-soft"
                label="Citations"
                value={data.recent_citations.length > 0
                  ? `${data.recent_citations.length}+`
                  : 0}
                onClick={() => navigate("/citations")}
              />
            </div>

            {/* ── Reading progress ── */}
            {data.library.total_papers > 0 && (
              <ReadingProgress
                unread={data.library.unread}
                reading={data.library.reading}
                read={data.library.read}
                total={data.library.total_papers}
              />
            )}

            {/* ── Main two-col grid ── */}
            <div className="grid gap-8 lg:grid-cols-2">

              {/* Currently reading */}
              {data.current_papers.length > 0 && (
                <section className="space-y-3">
                  <SectionHeader
                    icon={<BookMarked className="size-4" />}
                    title="Currently Reading"
                    action={{ label: "Library", onClick: () => navigate("/files?reading_status=reading") }}
                  />
                  <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
                    {data.current_papers.map((p) => (
                      <PaperRow
                        key={p.id}
                        paper={p}
                        onClick={() => navigate(`/papers/${p.id}`)}
                      />
                    ))}
                  </div>
                </section>
              )}

              {/* Recent papers */}
              <section className="space-y-3">
                <SectionHeader
                  icon={<Library className="size-4" />}
                  title="Recently Uploaded"
                  action={{ label: "View all", onClick: () => navigate("/files") }}
                />
                {data.recent_papers.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border p-6 text-center">
                    <p className="text-sm text-muted-foreground">No papers yet.</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Attach a PDF in any chat to add it to your library.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
                    {data.recent_papers.map((p) => (
                      <PaperRow
                        key={p.id}
                        paper={p}
                        onClick={() => navigate(`/papers/${p.id}`)}
                      />
                    ))}
                  </div>
                )}
              </section>

              {/* Recent chats */}
              <section className="space-y-3">
                <SectionHeader
                  icon={<MessageSquare className="size-4" />}
                  title="Recent Conversations"
                  action={{ label: "New chat", onClick: () => navigate("/") }}
                />
                {data.recent_chats.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border p-6 text-center">
                    <p className="text-sm text-muted-foreground">No chats yet.</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() => navigate("/")}
                    >
                      Start your first conversation
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
                    {data.recent_chats.map((c) => (
                      <ChatRow
                        key={c.id}
                        chat={c}
                        onClick={() =>
                          c.file_id
                            ? navigate(`/papers/${c.file_id}/chat/${c.id}`)
                            : navigate(`/c/${c.id}`)
                        }
                      />
                    ))}
                  </div>
                )}
              </section>

              {/* Recent citations */}
              {data.recent_citations.length > 0 && (
                <section className="space-y-3">
                  <SectionHeader
                    icon={<Quote className="size-4" />}
                    title="Recent Citations"
                    action={{ label: "View all", onClick: () => navigate("/citations") }}
                  />
                  <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
                    {data.recent_citations.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => navigate("/citations")}
                        className="flex w-full items-start gap-3 p-2.5 text-left transition-colors hover:bg-muted/60"
                      >
                        <Quote className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{c.title || "Untitled"}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {[c.authors?.split(";")[0]?.trim(), c.year].filter(Boolean).join(", ")}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              )}
            </div>

            {/* ── Projects ── */}
            {data.projects.length > 0 && (
              <section className="space-y-3">
                <SectionHeader
                  icon={<FolderKanban className="size-4" />}
                  title="Research Projects"
                  action={{ label: "Manage", onClick: () => navigate("/projects") }}
                />
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {data.projects.map((p) => (
                    <ProjectCard
                      key={p.id}
                      project={p}
                      onClick={() => openProject(p.id)}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* ── Top tags ── */}
            {data.library.top_tags.length > 0 && (
              <section className="space-y-3">
                <SectionHeader
                  icon={<Tag className="size-4" />}
                  title="Top Tags"
                  action={{ label: "Browse library", onClick: () => navigate("/files") }}
                />
                <div className="flex flex-wrap gap-2">
                  {data.library.top_tags.map(({ tag, count }) => (
                    <button
                      key={tag}
                      onClick={() => navigate(`/files?tag=${encodeURIComponent(tag)}`)}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
                    >
                      {tag}
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px]">{count}</span>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {/* bottom breathing room */}
            <div className="h-4" />
          </div>
        )}
      </div>
    </div>
  );
}
