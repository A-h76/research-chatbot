// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { UIProvider } from "@/context/UIContext";
import { PaperRelatedTab } from "./PaperRelatedTab";

afterEach(() => cleanup());
beforeEach(() => vi.unstubAllGlobals());

function mockFetchSequence(
  handlers: Array<(url: string, init?: RequestInit) => { status: number; body: unknown }>,
) {
  const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    const handler = handlers.shift();
    if (!handler) {
      return Promise.resolve({
        status: 500,
        ok: false,
        json: () => Promise.resolve({ error: "unexpected_fetch" }),
      });
    }
    const { status, body } = handler(String(url), init);
    return Promise.resolve({
      status,
      ok: status >= 200 && status < 300,
      json: () => Promise.resolve(body),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderTab(fileId = 9) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <UIProvider>
        <QueryClientProvider client={qc}>
          <PaperRelatedTab fileId={fileId} />
        </QueryClientProvider>
      </UIProvider>
    </MemoryRouter>,
  );
}

const sampleBundle = {
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
};

describe("PaperRelatedTab", () => {
  it("renders recommended / references sections from the related API", async () => {
    mockFetchSequence([
      () => ({ status: 200, body: sampleBundle }),
    ]);

    renderTab();

    expect(await screen.findByText("Recommended Read")).toBeTruthy();
    expect(screen.getByText("A Reference Paper")).toBeTruthy();
    expect(screen.getByText("Newer & recommended")).toBeTruthy();
    expect(screen.getByText("References")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: /Add to Library/i }).length).toBeGreaterThan(0);
  });

  it("adds a related paper to the library via discover/import", async () => {
    const fetchMock = mockFetchSequence([
      () => ({ status: 200, body: sampleBundle }),
      (url, init) => {
        expect(url).toContain("/api/discover/import");
        expect(init?.method).toBe("POST");
        const body = JSON.parse(String(init?.body || "{}"));
        expect(body.import_source).toBe("related");
        expect(body.title).toBe("Recommended Read");
        return {
          status: 201,
          body: {
            already_exists: false,
            file: { id: 77, title: "Recommended Read" },
          },
        };
      },
    ]);

    renderTab();
    const addButtons = await screen.findAllByRole("button", { name: /Add to Library/i });
    fireEvent.click(addButtons[0]);

    expect(await screen.findByText("Added")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shows a soft unavailable message when the provider is down", async () => {
    mockFetchSequence([
      () => ({ status: 503, body: { message: "unavailable", error: "related_unavailable" } }),
    ]);
    renderTab();
    expect(
      await screen.findByText("Related papers temporarily unavailable", {}, { timeout: 4000 }),
    ).toBeTruthy();
  });

  it("shows empty state when the bundle has no papers", async () => {
    mockFetchSequence([
      () => ({
        status: 200,
        body: {
          related: [],
          citing: [],
          recommended: [],
          cached_at: "",
          provider_version: "",
        },
      }),
    ]);
    renderTab();
    await waitFor(() => {
      expect(screen.getByText(/No related papers found/i)).toBeTruthy();
    });
  });
});
