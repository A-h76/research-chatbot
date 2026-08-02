import { describe, expect, it } from "vitest";
import {
  classifyAutosaveFailure,
  shouldResumeAutosaveOnOnline,
  shouldScheduleAutosave,
} from "./autosavePolicy";

describe("shouldScheduleAutosave", () => {
  it("skips while offline", () => {
    expect(
      shouldScheduleAutosave({ isOffline: true, saveState: "dirty" }),
    ).toBe(false);
  });

  it("skips while in conflict", () => {
    expect(
      shouldScheduleAutosave({ isOffline: false, saveState: "conflict" }),
    ).toBe(false);
  });

  it("allows dirty / scheduled / saved when online", () => {
    expect(
      shouldScheduleAutosave({ isOffline: false, saveState: "dirty" }),
    ).toBe(true);
    expect(
      shouldScheduleAutosave({ isOffline: false, saveState: "scheduled" }),
    ).toBe(true);
  });
});

describe("classifyAutosaveFailure", () => {
  it("detects version conflict payloads", () => {
    expect(classifyAutosaveFailure("version_conflict")).toBe("conflict");
    expect(classifyAutosaveFailure("Request failed 409")).toBe("conflict");
    expect(classifyAutosaveFailure("stale_document_version")).toBe("conflict");
  });

  it("treats other failures as error", () => {
    expect(classifyAutosaveFailure("network down")).toBe("error");
    expect(classifyAutosaveFailure("")).toBe("error");
  });
});

describe("shouldResumeAutosaveOnOnline", () => {
  it("resumes dirty/error/scheduled only", () => {
    expect(shouldResumeAutosaveOnOnline("dirty")).toBe(true);
    expect(shouldResumeAutosaveOnOnline("error")).toBe(true);
    expect(shouldResumeAutosaveOnOnline("scheduled")).toBe(true);
    expect(shouldResumeAutosaveOnOnline("conflict")).toBe(false);
    expect(shouldResumeAutosaveOnOnline("saved")).toBe(false);
  });
});
