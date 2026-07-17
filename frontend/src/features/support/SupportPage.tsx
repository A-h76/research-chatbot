import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/common/Toast";
import { LEGAL_LINKS } from "@/features/legal/content";
import { supportApi, type SupportCategory } from "./api";

const CATEGORIES: { value: SupportCategory; label: string }[] = [
  { value: "general", label: "General question" },
  { value: "bug", label: "Bug report" },
  { value: "feature", label: "Feature request" },
  { value: "account", label: "Account / data" },
];

const FAQ = [
  { q: "How do I export my chats?", a: "Settings → Data controls → Export your data. Choose PDF, Word, Markdown, Text, or JSON." },
  { q: "How do I delete my data?", a: "Settings → Data controls lets you delete all chats or your entire account." },
  { q: "Which files can I upload?", a: "PDF, Word, PowerPoint, Excel, text, code, images, and .zip archives (and folders)." },
  { q: "How fast will I hear back?", a: "We aim to respond within 2–3 business days." },
];

export function SupportPage() {
  const [email, setEmail] = useState("");
  const [category, setCategory] = useState<SupportCategory>("general");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<number | null>(null);

  const submit = async () => {
    setBusy(true);
    try {
      const res = await supportApi.submit({ email, category, subject, message });
      setDone(res.ticket);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not send message");
    } finally {
      setBusy(false);
    }
  };

  const canSend = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) && message.trim().length >= 5 && !busy;

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
        <h1 className="text-3xl font-semibold tracking-tight">Contact &amp; Support</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Have a question, found a bug, or want to request a feature? Send us a message.
        </p>

        {done ? (
          <div className="mt-8 flex items-start gap-3 rounded-xl border border-border bg-muted/40 p-5">
            <CheckCircle2 className="mt-0.5 size-5 text-green-500" />
            <div>
              <p className="font-medium">Message sent — ticket #{done}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                We emailed a confirmation to {email}. We'll reply within 2–3 business days.
              </p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => { setDone(null); setMessage(""); setSubject(""); }}>
                Send another
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-8 grid gap-4 rounded-xl border border-border p-5">
            <div className="grid gap-1.5">
              <Label htmlFor="s-email">Your email</Label>
              <Input id="s-email" type="email" value={email} placeholder="you@example.com"
                     onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label>Category</Label>
              <Select value={category} onValueChange={(v) => setCategory(v as SupportCategory)}>
                <SelectTrigger className="w-full sm:w-64"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="s-subject">Subject</Label>
              <Input id="s-subject" value={subject} placeholder="Short summary"
                     onChange={(e) => setSubject(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="s-message">Message</Label>
              <Textarea id="s-message" value={message} className="min-h-36"
                        placeholder="Tell us what's going on…"
                        onChange={(e) => setMessage(e.target.value)} />
            </div>
            <Button className="justify-self-end" disabled={!canSend} onClick={submit}>
              {busy ? "Sending…" : "Send message"}
            </Button>
          </div>
        )}

        <section className="mt-12">
          <h2 className="text-lg font-semibold">Frequently asked</h2>
          <div className="mt-4 divide-y divide-border rounded-xl border border-border">
            {FAQ.map((f) => (
              <div key={f.q} className="p-4">
                <p className="text-sm font-medium">{f.q}</p>
                <p className="mt-1 text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-5 gap-y-2 px-5 py-6 text-sm text-muted-foreground">
          {LEGAL_LINKS.map((l) => (
            <Link key={l.to} to={l.to} className="hover:text-foreground">{l.label}</Link>
          ))}
          <span className="ml-auto">© {new Date().getFullYear()} Personal AI</span>
        </div>
      </footer>
    </div>
  );
}
