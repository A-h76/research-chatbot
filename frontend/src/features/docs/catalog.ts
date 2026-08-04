/**
 * Docs catalog — living contracts + ADRs surfaced in Mintlify 3-col layout.
 * Bodies import from repo `docs/` (single source of truth).
 */
import apiContracts from "@repo-docs/contracts/api-contracts.md?raw";
import evidenceContract from "@repo-docs/contracts/evidence-contract.md?raw";
import errorContract from "@repo-docs/contracts/error-contract.md?raw";
import versioningPolicy from "@repo-docs/contracts/versioning-policy.md?raw";
import frontendCompatibility from "@repo-docs/contracts/frontend-compatibility.md?raw";
import jobObservability from "@repo-docs/contracts/job-observability.md?raw";
import researchScopeContract from "@repo-docs/contracts/research-scope-contract.md?raw";
import capabilityRouterContract from "@repo-docs/contracts/ai-capability-router-contract.md?raw";
import contractsReadme from "@repo-docs/contracts/README.md?raw";
import adr0016 from "@repo-docs/adr/0016-ai-capability-router.md?raw";
import adr0017 from "@repo-docs/adr/0017-research-scope-policy.md?raw";
import adr0003 from "@repo-docs/adr/0003-evidence-layer-canonical-contract.md?raw";
import adr0005 from "@repo-docs/adr/0005-freeze-evidence-layer-platform-contracts.md?raw";
import adr0001 from "@repo-docs/adr/0001-queue-backend.md?raw";
import adr0002 from "@repo-docs/adr/0002-ai-core-layer-boundaries.md?raw";
import adr0004 from "@repo-docs/adr/0004-research-intelligence-pipeline.md?raw";
import adr0006 from "@repo-docs/adr/0006-research-intelligence-staged-pipeline.md?raw";
import adr0007 from "@repo-docs/adr/0007-freeze-evidence-query-contract.md?raw";
import adr0015 from "@repo-docs/adr/0015-universal-full-text-resolution-v1.md?raw";

export type DocsNavItem = {
  slug: string;
  title: string;
  description?: string;
};

export type DocsNavGroup = {
  title: string;
  items: DocsNavItem[];
};

export type DocsPage = {
  slug: string;
  title: string;
  description?: string;
  body: string;
};

const OVERVIEW_BODY = `Dhund docs follow a **Mintlify-style** layout: sidebar navigation, readable prose, and an on-this-page table of contents.

## What lives here

| Area | Purpose |
|------|---------|
| **Contracts** | Living freeze for Evidence, RI, jobs, errors, and versioning |
| **API** | Public Evidence / RI / bindings / reviewer routes |
| **ADRs** | Why we chose the Capability Router, Research Scope, and Evidence platform |

Accent color stays Dhund **signal teal** — not Mintlify mint.

## Cognitive load

This surface answers one question: **How does this work?**

Use the sidebar to move between contracts. Use the right rail to jump within a page.
`;

export const DOCS_NAV: DocsNavGroup[] = [
  {
    title: "Start",
    items: [
      { slug: "overview", title: "Overview", description: "How Dhund docs are organised" },
      { slug: "contracts", title: "Living contracts", description: "Freeze hierarchy and version" },
    ],
  },
  {
    title: "API & platform",
    items: [
      { slug: "api-contracts", title: "API contracts", description: "Frozen Evidence / RI routes" },
      { slug: "evidence-contract", title: "Evidence contract", description: "Objects, stages, reviewer" },
      { slug: "error-contract", title: "Error contract", description: "Status matrix and bodies" },
      { slug: "job-observability", title: "Job observability", description: "A-404 enrichment" },
      { slug: "versioning", title: "Versioning policy", description: "When to bump contracts" },
      { slug: "frontend-compatibility", title: "Frontend compatibility", description: "SPA do / don’t" },
    ],
  },
  {
    title: "Research OS doctrine",
    items: [
      {
        slug: "capability-router",
        title: "Capability Router",
        description: "Job → Profile → Policy → Model",
      },
      {
        slug: "research-scope",
        title: "Research Scope",
        description: "ALLOW · CLARIFY · REDIRECT",
      },
    ],
  },
  {
    title: "ADRs",
    items: [
      { slug: "adr-0001", title: "ADR-0001 Queue backend" },
      { slug: "adr-0002", title: "ADR-0002 AI core boundaries" },
      { slug: "adr-0003", title: "ADR-0003 Evidence layer" },
      { slug: "adr-0004", title: "ADR-0004 RI pipeline" },
      { slug: "adr-0005", title: "ADR-0005 Platform freeze" },
      { slug: "adr-0006", title: "ADR-0006 Staged RI pipeline" },
      { slug: "adr-0007", title: "ADR-0007 Evidence query freeze" },
      { slug: "adr-0015", title: "ADR-0015 Full-text resolution" },
      { slug: "adr-0016", title: "ADR-0016 Capability Router" },
      { slug: "adr-0017", title: "ADR-0017 Research Scope" },
    ],
  },
];

const PAGES: DocsPage[] = [
  {
    slug: "overview",
    title: "Overview",
    description: "Documentation for the Research Operating System",
    body: OVERVIEW_BODY,
  },
  {
    slug: "contracts",
    title: "Living contracts",
    description: "Source of truth for Evidence / RI / jobs",
    body: contractsReadme,
  },
  {
    slug: "api-contracts",
    title: "API contracts",
    description: "A-402 freeze — Evidence / RI routes",
    body: apiContracts,
  },
  {
    slug: "evidence-contract",
    title: "Evidence contract",
    body: evidenceContract,
  },
  {
    slug: "error-contract",
    title: "Error contract",
    body: errorContract,
  },
  {
    slug: "job-observability",
    title: "Job observability",
    body: jobObservability,
  },
  {
    slug: "versioning",
    title: "Versioning policy",
    body: versioningPolicy,
  },
  {
    slug: "frontend-compatibility",
    title: "Frontend compatibility",
    body: frontendCompatibility,
  },
  {
    slug: "capability-router",
    title: "AI Capability Router",
    body: capabilityRouterContract,
  },
  {
    slug: "research-scope",
    title: "Research Scope",
    body: researchScopeContract,
  },
  { slug: "adr-0001", title: "ADR-0001", body: adr0001 },
  { slug: "adr-0002", title: "ADR-0002", body: adr0002 },
  { slug: "adr-0003", title: "ADR-0003", body: adr0003 },
  { slug: "adr-0004", title: "ADR-0004", body: adr0004 },
  { slug: "adr-0005", title: "ADR-0005", body: adr0005 },
  { slug: "adr-0006", title: "ADR-0006", body: adr0006 },
  { slug: "adr-0007", title: "ADR-0007", body: adr0007 },
  { slug: "adr-0015", title: "ADR-0015", body: adr0015 },
  { slug: "adr-0016", title: "ADR-0016", body: adr0016 },
  { slug: "adr-0017", title: "ADR-0017", body: adr0017 },
];

export const DOCS_BY_SLUG: Record<string, DocsPage> = Object.fromEntries(
  PAGES.map((p) => [p.slug, p]),
);

export const DEFAULT_DOCS_SLUG = "overview";

export function resolveDocsSlug(slug: string | undefined): DocsPage | null {
  const key = (slug || DEFAULT_DOCS_SLUG).trim().toLowerCase();
  return DOCS_BY_SLUG[key] ?? null;
}
