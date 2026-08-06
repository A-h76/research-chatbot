// @vitest-environment jsdom
import { describe, expect, it, vi, afterEach } from "vitest";
import { projectsApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("projectsApi.hub", () => {
  it("GET /api/projects/:id/hub", async () => {
    const hub = {
      project: {
        id: 1,
        name: "Thesis",
        emoji: "🔬",
        description: "",
        instructions: "",
        created_at: null,
      },
      stats: {
        papers: 0,
        chats: 0,
        memories: 0,
        notes: 0,
        open_questions: 0,
        insights: 0,
        unread: 0,
        reading: 0,
        read: 0,
        cross_paper_ready: 0,
      },
      recent_papers: [],
      recent_notes: [],
      open_questions: [],
      recent_insights: [],
      pipeline_summary: { done: 0, running: 0, pending: 0, failed: 0, partial: 0 },
      analysis_summary: { ready: 0, running: 0, pending: 0, failed: 0 },
      unread_activity: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(hub),
        }),
      ),
    );
    const data = await projectsApi.hub(1);
    expect(data.project.name).toBe("Thesis");
    expect(fetch).toHaveBeenCalled();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(String(url)).toContain("/api/projects/1/hub");
  });

  it("POST /api/projects/:id/questions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 201,
          json: () =>
            Promise.resolve({
              id: 9,
              project_id: 1,
              text: "What remains unanswered?",
              status: "open",
              source: "manual",
              linked_insight_id: null,
              created_at: null,
              updated_at: null,
            }),
        }),
      ),
    );
    const q = await projectsApi.createQuestion(1, {
      text: "What remains unanswered?",
    });
    expect(q.id).toBe(9);
    expect(q.status).toBe("open");
  });

  it("POST /api/projects/:id/research", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              id: 42,
              kind: "research",
              status: "running",
              preset: "evidence",
              query: "",
              file_ids: [1, 2],
              skipped: [],
              summary: "",
              answer: "",
              claims: [],
              supporting_file_ids: [],
              derived_analysis_id: 42,
              created_at: null,
            }),
        }),
      ),
    );
    const r = await projectsApi.runResearch(1, { preset: "evidence" });
    expect(r.id).toBe(42);
    expect(r.kind).toBe("research");
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(String(url)).toContain("/api/projects/1/research");
  });

  it("GET /api/projects/:id/memory", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              items: [
                {
                  id: 1,
                  project_id: 1,
                  fact: "Finding",
                  kind: "finding",
                  source: "research",
                  source_ref: "derived_analysis:9",
                  payload: { paper_ids: [2] },
                  pinned: false,
                  status: "active",
                  importance: 4,
                  claim_hash: "abc",
                  created_at: null,
                },
              ],
              total: 1,
            }),
        }),
      ),
    );
    const data = await projectsApi.listMemory(1);
    expect(data.total).toBe(1);
    expect(data.items[0]!.kind).toBe("finding");
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(String(url)).toContain("/api/projects/1/memory");
  });
});
