import { useEffect, useMemo, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { DocsLayout } from "./DocsLayout";
import { DEFAULT_DOCS_SLUG, resolveDocsSlug } from "./catalog";
import { applyHeadingIdsFromDom, type TocHeading } from "./toc";

/** Layout already shows the page title — avoid duplicate H1 from markdown. */
function stripLeadingH1(markdown: string): string {
  return markdown.replace(/^#[^#\n][^\n]*\n+/, "");
}

export function DocsPage() {
  const { slug } = useParams();
  const page = resolveDocsSlug(slug);
  const [toc, setToc] = useState<TocHeading[]>([]);
  const [articleEl, setArticleEl] = useState<HTMLDivElement | null>(null);

  const body = useMemo(() => (page ? stripLeadingH1(page.body) : ""), [page]);

  useEffect(() => {
    if (!articleEl || !body) {
      setToc([]);
      return;
    }
    const id = window.requestAnimationFrame(() => {
      setToc(applyHeadingIdsFromDom(articleEl));
    });
    return () => window.cancelAnimationFrame(id);
  }, [articleEl, body]);

  if (!page) {
    return <Navigate to={`/docs/${DEFAULT_DOCS_SLUG}`} replace />;
  }

  return (
    <DocsLayout title={page.title} description={page.description} toc={toc} contentKey={page.slug}>
      <div ref={setArticleEl}>
        <MarkdownRenderer content={body} className="prose-docs" />
      </div>
    </DocsLayout>
  );
}
