import { Link, useParams, Navigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { LEGAL, LEGAL_LINKS } from "./content";

export function LegalPage({ slug }: { slug?: string }) {
  const params = useParams();
  const key = slug ?? params.slug ?? "";
  const doc = LEGAL[key];
  if (!doc) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
          <Link to="/" className="flex items-center gap-2 text-sm font-medium">
            <span className="flex size-7 items-center justify-center rounded-full border border-border">✦</span>
            Personal AI
          </Link>
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-4" /> Back to app
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-10">
        <h1 className="text-3xl font-semibold tracking-tight">{doc.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">Last updated: {doc.updated}</p>
        <div className="mt-8">
          <MarkdownRenderer content={doc.body} />
        </div>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-5 gap-y-2 px-5 py-6 text-sm text-muted-foreground">
          {LEGAL_LINKS.map((l) => (
            <Link key={l.to} to={l.to} className="hover:text-foreground">
              {l.label}
            </Link>
          ))}
          <span className="ml-auto">© {new Date().getFullYear()} Personal AI</span>
        </div>
      </footer>
    </div>
  );
}
