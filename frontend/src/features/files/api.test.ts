import { describe, it, expect, vi, beforeEach } from "vitest";
import { filesApi } from "./api";

function mockFetch(responses: Record<string, { status: number; body: unknown }>) {
  const fetchMock = vi.fn((url: string, _opts?: RequestInit) => {
    const r = responses[url];
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

function makeFile(name: string) {
  return new File(["content"], name);
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("filesApi.upload", () => {
  it("routes document extensions through the JWT bridge to /api/documents/upload", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok123", refresh_token: "r" } },
      "/api/documents/upload": {
        status: 201,
        body: { document_id: 7, status: "PENDING", message: "Upload successful, processing started" },
      },
    });

    const outcome = await filesApi.upload(makeFile("paper.pdf"));

    expect(fetchMock.mock.calls.some((c) => c[0] === "/api/auth/jwt")).toBe(true);
    const uploadCall = fetchMock.mock.calls.find((c) => c[0] === "/api/documents/upload")!;
    expect((uploadCall[1] as RequestInit).headers).toEqual({ Authorization: "Bearer tok123" });
    expect(outcome).toEqual({
      async: true,
      result: { document_id: 7, status: "PENDING", message: "Upload successful, processing started" },
    });
  });

  it("routes image extensions through the session-authed /api/files, no JWT fetch", async () => {
    const fetchMock = mockFetch({
      "/api/files": {
        status: 200,
        body: { id: 3, name: "shot.png", kind: "image", size: 1, project_id: null, conversation_id: null, chunks: 0 },
      },
    });

    const outcome = await filesApi.upload(makeFile("shot.png"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalledWith("/api/auth/jwt", expect.anything());
    const uploadCall = fetchMock.mock.calls[0];
    expect(uploadCall[0]).toBe("/api/files");
    expect((uploadCall[1] as RequestInit).headers).toBeUndefined();
    expect(outcome.async).toBe(false);
  });
});

describe("filesApi.uploadFiles", () => {
  it("returns batch_id, total_files, and jobs on success", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok789", refresh_token: "r" } },
      "/api/uploads/bulk": {
        status: 201,
        body: {
          batch_id: 42,
          total_files: 2,
          jobs: [
            { job_id: 1, file_id: 101, filename: "a.pdf" },
            { job_id: 2, file_id: 102, filename: "b.epub" },
          ],
        },
      },
    });

    const result = await filesApi.uploadFiles([makeFile("a.pdf"), makeFile("b.epub")]);

    const uploadCall = fetchMock.mock.calls.find((c) => c[0] === "/api/uploads/bulk")!;
    expect((uploadCall[1] as RequestInit).headers).toEqual({ Authorization: "Bearer tok789" });
    expect(result.batch_id).toBe(42);
    expect(result.total_files).toBe(2);
    expect(result.jobs).toEqual([
      { job_id: 1, file_id: 101, filename: "a.pdf" },
      { job_id: 2, file_id: 102, filename: "b.epub" },
    ]);
  });

  it("propagates an ApiError when the batch is rejected (e.g. quota exceeded)", async () => {
    mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok789", refresh_token: "r" } },
      "/api/uploads/bulk": {
        status: 403,
        body: { error: "storage_quota_exceeded", message: "Storage quota exceeded" },
      },
    });

    await expect(filesApi.uploadFiles([makeFile("a.pdf")])).rejects.toThrow("storage_quota_exceeded");
  });
});

describe("filesApi.analyzeDocument", () => {
  it("bridges a JWT and POSTs to /api/documents/<id>/analysis", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok456", refresh_token: "r" } },
      "/api/documents/9/analysis": {
        status: 200,
        body: { document_id: 9, status: "done", model: "gpt-4o-mini", analysis: { executive_summary: "x" } },
      },
    });

    const result = await filesApi.analyzeDocument(9);

    const call = fetchMock.mock.calls.find((c) => c[0] === "/api/documents/9/analysis")!;
    expect((call[1] as RequestInit).method).toBe("POST");
    expect((call[1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer tok456" });
    expect(result.analysis.executive_summary).toBe("x");
  });
});
