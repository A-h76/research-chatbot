import { motion } from "framer-motion";
import { FileText, BookOpen, BarChart3, Code2, PenLine, Search } from "lucide-react";
import { SUGGESTIONS } from "@/lib/constants";

const ICONS = [FileText, BookOpen, BarChart3, Code2, PenLine, Search];

export function SuggestionCards({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto grid w-full max-w-3xl grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      {SUGGESTIONS.map((s, i) => {
        const Icon = ICONS[i % ICONS.length];
        return (
          <motion.button
            key={s.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.25 }}
            whileHover={{ y: -2 }}
            onClick={() => onPick(s.prompt)}
            className="group flex flex-col gap-2 rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:border-primary/30 hover:bg-hover"
          >
            <Icon className="size-4.5 text-primary" />
            <span className="text-sm font-medium">{s.title}</span>
          </motion.button>
        );
      })}
    </div>
  );
}
