/** Research Reviewer panel — severity accordion + empty state (B-511). */
/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ResearchReviewerPanel } from "./ResearchReviewerPanel";

vi.mock("@/features/evidence/api", () => ({
  evidenceApi: {
    latestReviewerRun: vi.fn(),
  },
}));

import { evidenceApi } from "@/features/evidence/api";

describe("ResearchReviewerPanel", () => {
  beforeEach(() => {
    vi.mocked(evidenceApi.latestReviewerRun).mockReset();
  });

  it("shows No issues when review has empty issues", async () => {
    vi.mocked(evidenceApi.latestReviewerRun).mockRejectedValue(new Error("none"));
    render(
      <ResearchReviewerPanel
        documentId={1}
        liveReview={{
          status: "pass",
          pass_rate: 1,
          sections_checked: 1,
          sections_passed: 1,
          issue_count: 0,
          reviewer_version: "1.1.0",
          issues: [],
        }}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText("No issues")).toBeTruthy();
    });
    expect(screen.getByText(/v1\.1\.0/)).toBeTruthy();
  });

  it("groups persisted findings by severity", async () => {
    vi.mocked(evidenceApi.latestReviewerRun).mockResolvedValue({
      id: 9,
      document_id: 1,
      project_id: 1,
      document_version_no: 1,
      writing_version: "2.0.0",
      reviewer_version: "1.1.0",
      status: "fail",
      pass_rate: 0,
      sections_checked: 1,
      sections_passed: 0,
      issue_count: 1,
      review: {
        status: "fail",
        pass_rate: 0,
        sections_checked: 1,
        sections_passed: 0,
        issue_count: 1,
        reviewer_version: "1.1.0",
        issues: [
          {
            code: "unbound_paragraph",
            severity: "error",
            section_id: "themes",
            message: "No bindings",
          },
        ],
      },
    });
    render(<ResearchReviewerPanel documentId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/blocks Accept\/export/)).toBeTruthy();
    });
    expect(screen.getByText(/run #9/)).toBeTruthy();
  });
});
