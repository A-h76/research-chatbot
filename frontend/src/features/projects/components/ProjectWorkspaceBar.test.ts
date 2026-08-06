import { describe, expect, it } from "vitest";
import { resolveWorkspaceActive } from "./ProjectWorkspaceBar";

describe("resolveWorkspaceActive", () => {
  it("highlights writing vs evidence focus", () => {
    expect(resolveWorkspaceActive("/writing", "", 1)).toBe("writing");
    expect(resolveWorkspaceActive("/writing", "?focus=evidence", 1)).toBe("evidence");
  });

  it("highlights paper tabs without double-matching papers", () => {
    expect(resolveWorkspaceActive("/papers/9", "", 1)).toBe("papers");
    expect(resolveWorkspaceActive("/papers/9", "?tab=evidence", 1)).toBe("evidence");
    expect(resolveWorkspaceActive("/papers/9", "?tab=graph", 1)).toBe("graph");
    expect(resolveWorkspaceActive("/papers/9/chat", "", 1)).toBe("chat");
  });

  it("highlights project hub tabs", () => {
    expect(resolveWorkspaceActive("/projects/3", "?tab=papers", 3)).toBe("papers");
    expect(resolveWorkspaceActive("/projects/3", "?tab=notes", 3)).toBe("notes");
    expect(resolveWorkspaceActive("/projects/3", "?tab=chat", 3)).toBe("chat");
    expect(resolveWorkspaceActive("/projects/3", "", 3)).toBeNull();
  });
});
