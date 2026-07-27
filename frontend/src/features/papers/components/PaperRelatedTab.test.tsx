// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PaperRelatedTab } from "./PaperRelatedTab";

afterEach(() => cleanup());
beforeEach(() => vi.unstubAllGlobals());

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      status,
      ok: status >= 200 && status < 300,
      json: () => Promise.resolve(body),
    }),
  );
}

function renderTab(fileId = 9) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PaperRelatedTab fileId={fileId} />
    </QueryClientProvider>,
  );
}

describe("PaperRelatedTab", () => {
  it("renders recommended / references sections from the related API", async () => {
    mockFetch(200, {
      related: [
        {
          paper_id: "ref1",
          doi: "10.1/ref",
          title: "A Reference Paper",
          authors: "Smith",
          year: 2021,
          venue: "JMLR",
          abstract: "",
          citation_count: 10,
          open_access_url: "",
          source: "s2",
        },
      ],
      citing: [],
      recommended: [
        {
          paper_id: "rec1",
          doi: "",
          title: "Recommended Read",
          authors: "Ada",
          year: 2024,
          venue: "",
          abstract: "short",
          citation_count: 0,
          open_access_url: "https://oa.example/x",
          source: "s2",
        },
      ],
      cached_at: "2026-07-01T00:00:00Z",
      provider_version: "v1",
    });

    renderTab();

    expect(await screen.findByText("Recommended Read")).toBeTruthy();
    expect(screen.getByText("A Reference Paper")).toBeTruthy();
    expect(screen.getByText("Recommended")).toBeTruthy();
    expect(screen.getByText("References")).toBeTruthy();
  });

  it("shows a soft unavailable message when the provider is down", async () => {
    mockFetch(503, { message: "unavailable" });
    renderTab();
    // Component sets retry: 1 — allow TanStack Query's backoff before error UI.
    expect(
      await screen.findByText("Related papers temporarily unavailable", {}, { timeout: 4000 }),
    ).toBeTruthy();
  });

  it("shows empty state when the bundle has no papers", async () => {
    mockFetch(200, {
      related: [],
      citing: [],
      recommended: [],
      cached_at: "",
      provider_version: "",
    });
    renderTab();
    await waitFor(() => {
      expect(screen.getByText(/No related papers found/i)).toBeTruthy();
    });
  });
});
