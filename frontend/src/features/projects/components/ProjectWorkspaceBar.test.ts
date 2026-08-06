import { describe, expect, it } from "vitest";
import {
  isProjectHubPath,
  resolveWorkspaceActive,
} from "./ProjectWorkspaceBar";

describe("isProjectHubPath", () => {
  it("matches the project hub only", () => {
    expect(isProjectHubPath("/projects/3", 3)).toBe(true);
    expect(isProjectHubPath("/projects/3/", 3)).toBe(true);
    expect(isProjectHubPath("/projects/3", 9)).toBe(false);
    expect(isProjectHubPath("/projects/3/settings", 3)).toBe(false);
    expect(isProjectHubPath("/papers/9", 3)).toBe(false);
  });
});

describe("resolveWorkspaceActive", () => {
  it("highlights writing vs evidence focus", () => {
    expect(resolveWorkspaceActive("/writing", "", 1)).toBe("writing");
    expect(resolveWorkspaceActive("/writing", "?focus=evidence", 1)).toBe("evidence");
    expect(resolveWorkspaceActive("/writing", "?focus=review", 1)).toBe("evidence");
    expect(resolveWorkspaceActive("/writing", "?tab=export", 1)).toBe("writing");
  });

  it("highlights paper tabs; graph demoted to papers chip", () => {
    expect(resolveWorkspaceActive("/papers/9", "", 1)).toBe("papers");
    expect(resolveWorkspaceActive("/papers/9", "?tab=evidence", 1)).toBe("evidence");
    expect(resolveWorkspaceActive("/papers/9", "?tab=graph", 1)).toBe("papers");
    expect(resolveWorkspaceActive("/papers/9/chat", "", 1)).toBe("chat");
  });

  it("does not highlight chips on the project hub (tabs own sections)", () => {
    expect(resolveWorkspaceActive("/projects/3", "?tab=papers", 3)).toBeNull();
    expect(resolveWorkspaceActive("/projects/3", "?tab=notes", 3)).toBeNull();
    expect(resolveWorkspaceActive("/projects/3", "?tab=chat", 3)).toBeNull();
    expect(resolveWorkspaceActive("/projects/3", "", 3)).toBeNull();
    expect(resolveWorkspaceActive("/projects/3/", "?tab=papers", 3)).toBeNull();
  });
});
