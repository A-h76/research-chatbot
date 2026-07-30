import { useNavigate, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import {
  Palette,
  Cpu,
  KeyRound,
  UserCog,
  Brain,
  Shield,
  Info,
  Database,
  Sparkles,
  FlaskConical,
  BookOpen,
  MessageSquare,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  AppearanceSection,
  ModelsSection,
  ApiSection,
  PersonalizationSection,
  MemorySection,
  PrivacySection,
  AboutSection,
  ChatDefaultsSection,
} from "../sections/Sections";
import { ResearchDefaultsSection } from "../sections/ResearchDefaultsSection";
import { DataControlsSection } from "../sections/DataControlsSection";
import { PromptsSection, TestAiSection } from "@/features/ai/sections/AiSections";
import { cn } from "@/lib/utils";

type SectionDef = {
  id: string;
  label: string;
  icon: typeof Palette;
  render: () => ReactNode;
  group: "main" | "advanced";
};

const SECTIONS: SectionDef[] = [
  { id: "appearance", label: "Appearance", icon: Palette, render: AppearanceSection, group: "main" },
  {
    id: "research",
    label: "Research defaults",
    icon: BookOpen,
    render: ResearchDefaultsSection,
    group: "main",
  },
  {
    id: "personalization",
    label: "Personalization",
    icon: UserCog,
    render: PersonalizationSection,
    group: "main",
  },
  { id: "memory", label: "Memory", icon: Brain, render: MemorySection, group: "main" },
  { id: "data", label: "Data controls", icon: Database, render: DataControlsSection, group: "main" },
  { id: "privacy", label: "Privacy", icon: Shield, render: PrivacySection, group: "main" },
  { id: "about", label: "About", icon: Info, render: AboutSection, group: "main" },
  { id: "models", label: "Models", icon: Cpu, render: ModelsSection, group: "advanced" },
  {
    id: "chat",
    label: "Chat defaults",
    icon: MessageSquare,
    render: ChatDefaultsSection,
    group: "advanced",
  },
  { id: "api", label: "API", icon: KeyRound, render: ApiSection, group: "advanced" },
  { id: "prompts", label: "AI Prompts", icon: Sparkles, render: PromptsSection, group: "advanced" },
  ...(import.meta.env.DEV
    ? ([
        {
          id: "ai-test",
          label: "Test AI (dev)",
          icon: FlaskConical,
          render: TestAiSection,
          group: "advanced" as const,
        },
      ] satisfies SectionDef[])
    : []),
];

export function SettingsPage() {
  const { section } = useParams();
  const navigate = useNavigate();
  const active = SECTIONS.find((s) => s.id === section) ?? SECTIONS[0];
  const ActiveComponent = active.render;

  const main = SECTIONS.filter((s) => s.group === "main");
  const advanced = SECTIONS.filter((s) => s.group === "advanced");

  function NavButton({ s }: { s: SectionDef }) {
    const Icon = s.icon;
    return (
      <button
        type="button"
        onClick={() => navigate(`/settings/${s.id}`)}
        className={cn(
          "flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors",
          active.id === s.id
            ? "bg-muted font-medium text-foreground"
            : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
        )}
      >
        <Icon className="size-4" />
        {s.label}
      </button>
    );
  }

  return (
    <PageContainer title="Settings">
      <div className="flex flex-col gap-6 lg:flex-row">
        <nav className="flex gap-1 overflow-x-auto lg:w-52 lg:shrink-0 lg:flex-col">
          {main.map((s) => (
            <NavButton key={s.id} s={s} />
          ))}
          {advanced.length > 0 && (
            <>
              <p className="mt-3 hidden px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground lg:block">
                Advanced
              </p>
              {advanced.map((s) => (
                <NavButton key={s.id} s={s} />
              ))}
            </>
          )}
        </nav>
        <div className="min-w-0 flex-1">
          <h2 className="mb-1 text-lg font-semibold tracking-tight">{active.label}</h2>
          <ActiveComponent />
        </div>
      </div>
    </PageContainer>
  );
}
