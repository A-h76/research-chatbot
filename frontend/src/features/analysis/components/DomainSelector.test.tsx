// @vitest-environment jsdom
//
// The only component test in this repo (see features/*/api.test.ts for
// the existing convention — those test fetch wrappers under the default
// node environment). This file needs a real DOM, so it opts into jsdom
// per-file via the pragma above rather than changing vite.config.ts's
// global `environment: "node"` default and affecting every other test.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DomainSelector } from "./DomainSelector";

// vite.config.ts sets globals: false (matching this repo's other tests),
// so @testing-library/react's usual auto-registered afterEach cleanup
// never fires — without this, DOM from earlier tests in this file stays
// mounted and later getByText/getByRole queries match multiple elements.
afterEach(() => cleanup());

describe("DomainSelector", () => {
  it("renders with auto-detect selected by default", () => {
    render(<DomainSelector value={null} onChange={vi.fn()} />);
    expect(screen.getByLabelText("Select paper domain").textContent).toContain("Auto-detect");
  });

  it("calls onChange with the domain key when an option is selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainSelector value={null} onChange={onChange} />);

    await user.click(screen.getByLabelText("Select paper domain"));
    await user.click(await screen.findByRole("option", { name: "Medical" }));

    expect(onChange).toHaveBeenCalledWith("medical");
  });

  it("calls onChange with null when auto-detect is re-selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainSelector value="medical" onChange={onChange} />);

    await user.click(screen.getByLabelText("Select paper domain"));
    await user.click(await screen.findByRole("option", { name: "Auto-detect" }));

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("clicking the detected-domain badge applies it", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainSelector value={null} onChange={onChange} detectedDomain="medical" />);

    await user.click(screen.getByText("Detected: Medical"));

    expect(onChange).toHaveBeenCalledWith("medical");
  });

  it("shows the auto-detected style once the selection matches the detection", () => {
    render(<DomainSelector value="medical" onChange={vi.fn()} detectedDomain="medical" />);
    expect(screen.getByText("Auto-detected: Medical")).toBeTruthy();
  });

  it("disables interaction and dims the badge when disabled", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DomainSelector value={null} onChange={onChange} detectedDomain="medical" disabled />);

    const badge = screen.getByText("Detected: Medical");
    await user.click(badge);

    expect(onChange).not.toHaveBeenCalled();
    expect(badge.className).toMatch(/opacity-50/);
  });
});
