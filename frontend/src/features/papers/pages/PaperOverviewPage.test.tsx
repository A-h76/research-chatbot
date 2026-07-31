// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PaperOverviewPage } from "./PaperOverviewPage";
import type { UserFile } from "@/types/api";

afterEach(() => cleanup());
beforeEach(() => vi.unstubAllGlobals());

type MockResponse = { status: number; body: unknown };

function mockFetch(responses: Record<string, MockResponse | MockResponse[]>) {
  const callCounts: Record<string, number> = {};
  const fetchMock = vi.fn((url: string, _opts?: RequestInit) => {
    const path = String(url).split("?")[0]!;
    const entry = responses[url] ?? responses[path];
    if (!entry) throw new Error(`unexpected fetch to ${url}`);
    const seq = Array.isArray(entry) ? entry : [entry];
    const i = callCounts[path] ?? callCounts[url] ?? 0;
    callCounts[path] = i + 1;
    const r = seq[Math.min(i, seq.length - 1)]!;
    return Promise.resolve({
      status: r.status,
      ok: r.status >= 200 && r.status < 300,
      json: () => Promise.resolve(r.body),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const FILE: UserFile = {
  id: 9,
  name: "paper.pdf",
  kind: "document",
  size: 1024,
  project_id: null,
  conversation_id: null,
  chunks: 5,
  title: "",
  authors: "",
  year: "",
  venue: "",
  doi: "",
  abstract: "",
  reading_status: "unread",
  tags: [],
  meta_status: "done",
  created_at: null,
};

const NO_ANALYSIS = { file_id: 9, status: "none", error: "", model: "", updated_at: null, data: {} };

const PIPELINE_404 = {
  "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
  "/api/documents/9/pipeline": {
    status: 404,
    body: { error: "not_found", message: "No Phase 1 analysis yet" },
  },
};

function renderPage(entry = "/papers/9?tab=narrative") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/papers/:fileId" element={<PaperOverviewPage />} />
          <Route path="/papers/:fileId/chat" element={<div>chat-page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Paper Workspace shell (M4)", () => {
  it("renders tablist and Overview by default", async () => {
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");

    await screen.findByRole("heading", { name: "paper.pdf" });
    expect(screen.getByRole("tablist", { name: "Paper workspace" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Overview" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: "Structure" })).toBeTruthy();
  });

  it("shows Structure tab content from document understanding (or empty)", async () => {
    const user = userEvent.setup();
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");
    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByRole("tab", { name: "Structure" }));
    expect(await screen.findByText(/no structure yet/i)).toBeTruthy();
  });

  it("shows Research Profile tab empty state when phase is missing", async () => {
    const user = userEvent.setup();
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");
    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByRole("tab", { name: "Research Profile" }));
    expect(await screen.findByText(/no research profile yet/i)).toBeTruthy();
  });

  it("shows Entities tab empty state when phase is missing", async () => {
    const user = userEvent.setup();
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");
    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByRole("tab", { name: "Entities" }));
    expect(await screen.findByText(/no entities yet/i)).toBeTruthy();
  });

  it("shows Evidence tab empty state when phase is missing", async () => {
    const user = userEvent.setup();
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");
    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByRole("tab", { name: "Evidence" }));
    expect(await screen.findByText(/no evidence grading yet/i)).toBeTruthy();
  });

  it("shows Knowledge Graph tab empty state when phase is missing", async () => {
    const user = userEvent.setup();
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9");
    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByRole("tab", { name: "Knowledge Graph" }));
    expect(await screen.findByText(/no knowledge graph yet/i)).toBeTruthy();
  });

  it("deep-links Narrative via ?tab=narrative", async () => {
    mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9?tab=narrative");
    await screen.findByRole("heading", { name: "paper.pdf" });
    expect(screen.getByRole("tab", { name: "Narrative" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByLabelText("Select paper domain")).toBeTruthy();
  });
});

describe("PaperOverviewPage — single-paper analysis", () => {
  it("posts the selected domain, metadata, and question, then renders the result", async () => {
    const user = userEvent.setup();
    const fetchMock = mockFetch({
      "/api/files/9": { status: 200, body: FILE },
      "/api/files/9/analysis": [
        { status: 200, body: NO_ANALYSIS },
        {
          status: 200,
          body: {
            file_id: 9,
            status: "done",
            error: "",
            model: "gpt-4o-mini",
            updated_at: "2026-01-01T00:00:00Z",
            data: { executive_summary: "Great paper" },
          },
        },
      ],
      ...PIPELINE_404,
      "/api/documents/9/analysis": {
        status: 200,
        body: {
          document_id: 9,
          status: "done",
          model: "gpt-4o-mini",
          analysis: { executive_summary: "Great paper" },
          domain_detected: "medical",
        },
      },
    });

    renderPage("/papers/9?tab=narrative");

    await screen.findByRole("heading", { name: "paper.pdf" });

    await user.click(screen.getByLabelText("Select paper domain"));
    await user.click(await screen.findByRole("option", { name: "Medical" }));

    await user.type(screen.getByLabelText("Your question (optional)"), "methodology?");

    await user.click(screen.getByRole("button", { name: /advanced metadata/i }));
    await user.type(await screen.findByLabelText("Title"), "My Title");

    await user.click(screen.getByRole("button", { name: /^analyze paper$/i }));

    expect(await screen.findByText("Great paper")).toBeTruthy();

    const call = fetchMock.mock.calls.find((c) => c[0] === "/api/documents/9/analysis")!;
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body).toEqual({
      domain: "medical",
      metadata: { title: "My Title", authors: "", venue: "", year: "" },
      user_query: "methodology?",
    });

    expect(screen.getByText("Auto-detected: Medical")).toBeTruthy();
  }, 15000);

  it("hides the analysis form and shows a processing message while the paper is still being imported", async () => {
    mockFetch({
      "/api/files/9": { status: 200, body: { ...FILE, meta_status: "pending" } },
      "/api/files/9/analysis": { status: 200, body: NO_ANALYSIS },
      ...PIPELINE_404,
    });

    renderPage("/papers/9?tab=narrative");

    expect(await screen.findByText(/still being processed/i)).toBeTruthy();
    expect(screen.queryByLabelText("Select paper domain")).toBeNull();
  });
});
