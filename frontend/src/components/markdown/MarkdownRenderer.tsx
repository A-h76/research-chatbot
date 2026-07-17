import { useEffect, useRef } from "react";
import { renderMarkdown, highlightElement } from "@/lib/markdown";

function decorateCodeBlocks(container: HTMLElement) {
  container.querySelectorAll("pre").forEach((pre) => {
    if (pre.querySelector(".codehead")) return;
    const code = pre.querySelector("code");
    if (!code) return;
    const langMatch = code.className.match(/language-(\w+)/);
    const lang = langMatch ? langMatch[1] : "";

    const head = document.createElement("div");
    head.className = "codehead";
    const label = document.createElement("span");
    label.textContent = lang || "code";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(code.textContent || "");
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = "Copy"), 1500);
    });
    head.appendChild(label);
    head.appendChild(btn);
    pre.insertBefore(head, code);
    highlightElement(code as HTMLElement);
  });
}

export function MarkdownRenderer({ content }: { content: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const html = renderMarkdown(content);

  useEffect(() => {
    if (ref.current) decorateCodeBlocks(ref.current);
  }, [html]);

  return (
    <div
      ref={ref}
      className="prose-chat"
      // Content is sanitized by DOMPurify inside renderMarkdown().
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
