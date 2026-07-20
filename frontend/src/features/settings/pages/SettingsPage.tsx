import { useNavigate, useParams } from "react-router-dom";
import { Palette, Cpu, KeyRound, UserCog, Brain, Shield, Info, Database, Sparkles, FlaskConical } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  AppearanceSection,
  ModelsSection,
  ApiSection,
  PersonalizationSection,
  MemorySection,
  PrivacySection,
  AboutSection,
} from "../sections/Sections";
import { DataControlsSection } from "../sections/DataControlsSection";
import { PromptsSection, TestAiSection } from "@/features/ai/sections/AiSections";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { id: "appearance", label: "Appearance", icon: Palette, render: AppearanceSection },
  { id: "models", label: "Models", icon: Cpu, render: ModelsSection },
  { id: "api", label: "API", icon: KeyRound, render: ApiSection },
  { id: "personalization", label: "Personalization", icon: UserCog, render: PersonalizationSection },
  { id: "memory", label: "Memory", icon: Brain, render: MemorySection },
  { id: "data", label: "Data controls", icon: Database, render: DataControlsSection },
  { id: "privacy", label: "Privacy", icon: Shield, render: PrivacySection },
  { id: "prompts", label: "AI Prompts", icon: Sparkles, render: PromptsSection },
  // Dev build only — excluded entirely from a production bundle (not just
  // hidden), same reasoning as App.tsx's React Query Devtools gate. The
  // backend's own IS_PRODUCTION check on POST /api/ai/test is the real
  // guard; this just keeps the entry point out of the nav in production too.
  ...(import.meta.env.DEV
    ? [{ id: "ai-test", label: "Test AI (dev)", icon: FlaskConical, render: TestAiSection }]
    : []),
  { id: "about", label: "About", icon: Info, render: AboutSection },
];

export function SettingsPage() {
  const { section } = useParams();
  const navigate = useNavigate();
  const active = SECTIONS.find((s) => s.id === section) ?? SECTIONS[0];
  const ActiveComponent = active.render;

  return (
    <PageContainer title="Settings">
      <div className="flex flex-col gap-6 lg:flex-row">
        <nav className="flex gap-1 overflow-x-auto lg:w-52 lg:shrink-0 lg:flex-col">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => navigate(`/settings/${s.id}`)}
                className={cn(
                  "flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors",
                  active.id === s.id
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                )}
              >
                <Icon className="size-4" />
                {s.label}
              </button>
            );
          })}
        </nav>
        <div className="min-w-0 flex-1">
          <ActiveComponent />
        </div>
      </div>
    </PageContainer>
  );
}
