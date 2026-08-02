import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ShieldOff,
  MailPlus,
  BarChart3,
  ScrollText,
  Flag,
  Gauge,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { cn } from "@/lib/utils";
import { AdminGate } from "../AdminGate";
import { KillSwitchPanel } from "../components/KillSwitchPanel";
import { InvitesPanel } from "../components/InvitesPanel";
import { BetaMetricsPanel } from "../components/BetaMetricsPanel";
import { SecurityEventsPanel } from "../components/SecurityEventsPanel";
import { FeatureFlagsPanel } from "../components/FeatureFlagsPanel";
import { QuotasPanel } from "../components/QuotasPanel";
import { WorkerHealthChip } from "../components/WorkerHealthChip";

const SECTIONS = [
  { id: "kill-switch", label: "Kill switch", icon: ShieldOff, render: KillSwitchPanel },
  { id: "invites", label: "Invites", icon: MailPlus, render: InvitesPanel },
  { id: "metrics", label: "Beta metrics", icon: BarChart3, render: BetaMetricsPanel },
  { id: "events", label: "Security events", icon: ScrollText, render: SecurityEventsPanel },
  { id: "flags", label: "Feature flags", icon: Flag, render: FeatureFlagsPanel },
  { id: "quotas", label: "Quotas", icon: Gauge, render: QuotasPanel },
] as const;

export function AdminPage() {
  return (
    <AdminGate>
      <AdminPageInner />
    </AdminGate>
  );
}

function AdminPageInner() {
  const { section } = useParams();
  const navigate = useNavigate();
  const active = useMemo(
    () => SECTIONS.find((s) => s.id === section) ?? SECTIONS[0],
    [section],
  );
  const Active = active.render;

  return (
    <PageContainer
      title="Admin"
      description="Closed-beta ops — invites, AI kill switch, quotas, metrics, and audit events."
      maxWidth="6xl"
      actions={<WorkerHealthChip />}
    >
      <div className="flex flex-col gap-6 md:flex-row">
        <nav className="flex shrink-0 gap-1 overflow-x-auto md:w-44 md:flex-col md:overflow-visible">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const isActive = s.id === active.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => navigate(`/admin/${s.id}`)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-left text-[13px] transition-colors",
                  isActive
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <Icon className="size-3.5 shrink-0" />
                {s.label}
              </button>
            );
          })}
        </nav>
        <div className="min-w-0 flex-1">
          <h2 className="mb-4 text-sm font-semibold tracking-tight">{active.label}</h2>
          <Active />
        </div>
      </div>
    </PageContainer>
  );
}
