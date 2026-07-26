import { describe, it, expect, vi, beforeEach } from "vitest";
import { pipelineApi } from "./api";
import { PipelineError } from "./errors";
import { adaptPipeline } from "./adapter";
import type { PipelineDocument } from "./types";

function mockFetch(responses: Record<string, { status: number; body: unknown }>) {
  const fetchMock = vi.fn((url: string, _opts?: RequestInit) => {
    const path = url.split("?")[0]!;
    const r = responses[url] ?? responses[path];
    if (!r) throw new Error(`unexpected fetch to ${url}`);
    return Promise.resolve({
      status: r.status,
      ok: r.status >= 200 && r.status < 300,
      json: () => Promise.resolve(r.body),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const SAMPLE: PipelineDocument = {
  file_id: 9,
  content_hash: "abc",
  status: "done",
  pipeline_version: "1.0",
  total_processing_time_ms: 12,
  warnings: [],
  errors: [],
  phases: ["document_understanding", "classification"],
  phase_results: {
    document_understanding: { ok: true },
    classification: { domain: "medical" },
  },
};

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("pipelineApi", () => {
  it("GETs pipeline with JWT and returns typed document", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/pipeline": { status: 200, body: SAMPLE },
    });

    const doc = await pipelineApi.getPipeline(9);

    expect(fetchMock.mock.calls.some((c) => c[0] === "/api/auth/jwt")).toBe(true);
    const call = fetchMock.mock.calls.find((c) => c[0] === "/api/documents/9/pipeline")!;
    expect((call[1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer tok" });
    expect(doc?.file_id).toBe(9);
    expect(doc?.status).toBe("done");
  });

  it("returns null when pipeline is absent (404)", async () => {
    mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/pipeline": {
        status: 404,
        body: { error: "not_found", message: "No Phase 1 analysis yet" },
      },
    });

    await expect(pipelineApi.getPipeline(9)).resolves.toBeNull();
  });

  it("GETs a single phase", async () => {
    mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/phases/classification": {
        status: 200,
        body: { document_id: 9, phase: "classification", result: { domain: "medical" } },
      },
    });

    const res = await pipelineApi.getPhase(9, "classification");
    expect(res.document_id).toBe(9);
    expect(res.result.domain).toBe("medical");
  });

  it("POSTs analyze and returns queued 202 body", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/analyze": {
        status: 202,
        body: {
          status: "queued",
          job_id: 44,
          document_id: 9,
          job_type: "phase1_analysis",
        },
      },
    });

    const res = await pipelineApi.startAnalysis(9);
    expect(res).toEqual({
      status: "queued",
      job_id: 44,
      document_id: 9,
      job_type: "phase1_analysis",
    });
    const call = fetchMock.mock.calls.find((c) => c[0] === "/api/documents/9/analyze")!;
    expect((call[1] as RequestInit).method).toBe("POST");
  });

  it("POSTs sync analyze with ?sync=1", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/analyze?sync=1": { status: 200, body: SAMPLE },
    });

    const res = await pipelineApi.startAnalysis(9, { sync: true, force: true });
    expect(res).toMatchObject({ file_id: 9, status: "done" });
    const call = fetchMock.mock.calls.find((c) =>
      String(c[0]).startsWith("/api/documents/9/analyze"),
    )!;
    expect(call[0]).toBe("/api/documents/9/analyze?sync=1");
    expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({
      force: true,
      sync: true,
    });
  });

  it("maps 500 to PipelineError server_error", async () => {
    mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/documents/9/pipeline": {
        status: 500,
        body: { error: "boom" },
      },
    });

    try {
      await pipelineApi.getPipeline(9);
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(PipelineError);
      expect(err).toMatchObject({ code: "server_error", status: 500 });
    }
  });
});

describe("adaptPipeline", () => {
  it("marks absent when doc is null", () => {
    const d = adaptPipeline(null);
    expect(d.uiState).toBe("absent");
    expect(d.isAbsent).toBe(true);
    expect(d.completed).toEqual([]);
    expect(d.remaining).toHaveLength(7);
  });

  it("marks queued when enqueuePending and no row", () => {
    const d = adaptPipeline(null, { enqueuePending: true });
    expect(d.uiState).toBe("queued");
    expect(d.isQueued).toBe(true);
  });

  it("marks ready and exposes completed / remaining phases", () => {
    const d = adaptPipeline(SAMPLE);
    expect(d.uiState).toBe("ready");
    expect(d.isReady).toBe(true);
    expect(d.completed).toEqual(["document_understanding", "classification"]);
    expect(d.currentPhase).toBe("classification");
    expect(d.remaining[0]).toBe("analysis_context");
    expect(d.remaining).not.toContain("document_understanding");
  });
  it("marks stale on content hash mismatch", () => {
    const d = adaptPipeline(SAMPLE, { fileContentHash: "other" });
    expect(d.uiState).toBe("stale");
    expect(d.isStale).toBe(true);
  });

  it("marks error on failed status", () => {
    const d = adaptPipeline({ ...SAMPLE, status: "failed" });
    expect(d.uiState).toBe("error");
    expect(d.isError).toBe(true);
    expect(d.failedPhase).toBe("classification");
  });

  it("marks running for running status", () => {
    const d = adaptPipeline({ ...SAMPLE, status: "running" });
    expect(d.isRunning).toBe(true);
  });
});
