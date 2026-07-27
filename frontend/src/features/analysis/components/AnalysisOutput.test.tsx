// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { AnalysisOutput } from "./AnalysisOutput";

afterEach(() => cleanup());

const MEDICAL_MIN = 17;
const MEDICAL_MAX = 30;

function buildAnalysis(n = 30): string {
  const parts: string[] = [];
  for (let i = 1; i <= n; i++) {
    parts.push(`## ${i}. Section Heading ${i}\nContent for section ${i}.`);
  }
  return parts.join("\n\n");
}

describe("AnalysisOutput", () => {
  it("renders exactly 30 sections from a sample analysis with 30 numbered sections", () => {
    const { container } = render(<AnalysisOutput analysis={buildAnalysis(30)} />);

    const items = container.querySelectorAll('[data-slot="accordion-item"]');
    expect(items.length).toBe(30);
  });

  it("marks sections 17-30 as medical (badge + border) and leaves 1-16 unmarked", () => {
    const { container } = render(<AnalysisOutput analysis={buildAnalysis(30)} />);

    const items = Array.from(container.querySelectorAll('[data-slot="accordion-item"]'));
    expect(items).toHaveLength(30);

    items.forEach((item, i) => {
      const sectionNumber = i + 1;
      const isMedical = sectionNumber >= MEDICAL_MIN && sectionNumber <= MEDICAL_MAX;
      expect(item.hasAttribute("data-medical")).toBe(isMedical);
      expect(item.className.includes("border-l")).toBe(isMedical);
    });

    // One 🩺 badge per medical section (17..30 inclusive = 14 sections).
    expect(screen.getAllByText("🩺")).toHaveLength(MEDICAL_MAX - MEDICAL_MIN + 1);
  });

  it("renders nothing when analysis is falsy", () => {
    const { container } = render(<AnalysisOutput analysis="" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows a placeholder for a section with no content", () => {
    render(<AnalysisOutput analysis={"## 1. Empty Section\n\n## 2. Has Content\nSome text."} />);
    expect(screen.getByText("No content available")).toBeTruthy();
  });
});
