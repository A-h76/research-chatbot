// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PromptsSection } from "./AiSections";

afterEach(() => cleanup());
beforeEach(() => vi.unstubAllGlobals());

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      status,
      ok: status >= 200 && status < 300,
      json: () => Promise.resolve(body),
    }),
  );
}

function renderSection() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PromptsSection />
    </QueryClientProvider>,
  );
}

describe("PromptsSection (PromptBuilder UI)", () => {
  it("lists seeded prompt templates from /api/ai/prompts", async () => {
    mockFetchOnce(200, {
      prompts: [
        {
          name: "chat_system",
          version: 2,
          template: "You are a helpful research assistant.",
          is_active: true,
          created_at: null,
        },
        {
          name: "paper_analysis",
          version: 1,
          template: "Analyse the paper…",
          is_active: true,
          created_at: null,
        },
      ],
    });

    renderSection();

    expect(await screen.findByText("chat_system")).toBeTruthy();
    expect(screen.getByText("paper_analysis")).toBeTruthy();
    expect(screen.getByText("You are a helpful research assistant.")).toBeTruthy();
    expect(screen.getAllByText("active").length).toBeGreaterThan(0);
  });

  it("shows empty state when no prompts are seeded", async () => {
    mockFetchOnce(200, { prompts: [] });
    renderSection();
    expect(await screen.findByText("No prompts seeded yet")).toBeTruthy();
  });

  it("surfaces a load error when the prompts API fails", async () => {
    mockFetchOnce(500, { error: "server_error" });
    renderSection();
    expect(await screen.findByText(/Could not load prompts/i)).toBeTruthy();
  });
});
