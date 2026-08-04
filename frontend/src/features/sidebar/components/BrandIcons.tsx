/** Brand marks for Library / Integrations — bundled via Vite (works in SPA catch-all). */

import { cn } from "@/lib/utils";
import zoteroIconUrl from "@/assets/brand/zotero.ico";
import mendeleyIconUrl from "@/assets/brand/mendeley.svg";
import openalexIconUrl from "@/assets/brand/openalex.png";
import semanticScholarIconUrl from "@/assets/brand/semanticscholar.png";
import jabrefIconUrl from "@/assets/brand/jabref.png";

/** Static Flask-served marks (same files as landing ecosystem). */
const STATIC = {
  bibtex: "/static/brands/bibtex.svg",
  ris: "/static/brands/ris.svg",
  crossref: "/static/brands/crossref.svg",
  paperpile: "/static/brands/paperpile.svg",
  readcube: "/static/brands/readcube.svg",
  webhooks: "/static/brands/webhooks.svg",
  pubmed: "/static/brands/pubmed.svg",
  arxiv: "/static/brands/arxiv.svg",
  orcid: "/static/brands/orcid.svg",
} as const;

function BrandImg({
  src,
  className,
  alt = "",
}: {
  src: string;
  className?: string;
  alt?: string;
}) {
  return (
    <img
      src={src}
      alt={alt}
      width={16}
      height={16}
      className={cn("size-4 shrink-0 object-contain", className)}
      draggable={false}
    />
  );
}

export function ZoteroIcon({ className }: { className?: string }) {
  return <BrandImg src={zoteroIconUrl} className={className} />;
}

export function MendeleyIcon({ className }: { className?: string }) {
  return <BrandImg src={mendeleyIconUrl} className={className} />;
}

export function OpenAlexIcon({ className }: { className?: string }) {
  return <BrandImg src={openalexIconUrl} className={className} />;
}

export function SemanticScholarIcon({ className }: { className?: string }) {
  return <BrandImg src={semanticScholarIconUrl} className={className} />;
}

export function JabRefIcon({ className }: { className?: string }) {
  return <BrandImg src={jabrefIconUrl} className={className} />;
}

export function BibtexIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.bibtex} className={className} />;
}

export function RisIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.ris} className={className} />;
}

export function CrossrefIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.crossref} className={className} />;
}

export function PaperpileIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.paperpile} className={className} />;
}

export function ReadCubeIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.readcube} className={className} />;
}

export function WebhooksIcon({ className }: { className?: string }) {
  return <BrandImg src={STATIC.webhooks} className={className} />;
}

/** Resolve a catalog provider id → brand icon (or null). */
export function BrandIconForProvider({
  id,
  className,
}: {
  id: string;
  className?: string;
}) {
  switch (id) {
    case "zotero":
      return <ZoteroIcon className={className} />;
    case "mendeley":
      return <MendeleyIcon className={className} />;
    case "openalex":
      return <OpenAlexIcon className={className} />;
    case "semantic_scholar":
      return <SemanticScholarIcon className={className} />;
    case "jabref":
      return <JabRefIcon className={className} />;
    case "bibtex":
      return <BibtexIcon className={className} />;
    case "ris":
      return <RisIcon className={className} />;
    case "crossref":
      return <CrossrefIcon className={className} />;
    case "paperpile":
      return <PaperpileIcon className={className} />;
    case "readcube":
      return <ReadCubeIcon className={className} />;
    case "webhooks":
      return <WebhooksIcon className={className} />;
    default:
      return null;
  }
}
