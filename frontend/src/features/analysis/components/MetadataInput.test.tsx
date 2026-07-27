// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MetadataInput } from "./MetadataInput";

afterEach(() => cleanup());

const EMPTY = { title: "", authors: "", venue: "", year: "" };

describe("MetadataInput", () => {
  it("renders collapsed by default with the toggle visible and fields hidden", () => {
    render(<MetadataInput value={EMPTY} onChange={vi.fn()} />);

    const toggle = screen.getByRole("button", { name: /advanced metadata/i });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByLabelText("Title")).toBeNull();
  });

  it("renders with initial metadata when expanded", () => {
    render(
      <MetadataInput
        value={{ title: "Attention Is All You Need", authors: "Vaswani et al.", venue: "NeurIPS", year: "2017" }}
        onChange={vi.fn()}
        defaultOpen
      />
    );

    expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Attention Is All You Need");
    expect((screen.getByLabelText("Authors") as HTMLInputElement).value).toBe("Vaswani et al.");
    expect((screen.getByLabelText("Venue") as HTMLInputElement).value).toBe("NeurIPS");
    expect((screen.getByLabelText("Year") as HTMLInputElement).value).toBe("2017");
  });

  it("clicking the toggle expands the section", async () => {
    const user = userEvent.setup();
    render(<MetadataInput value={EMPTY} onChange={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /advanced metadata/i }));

    expect(await screen.findByLabelText("Title")).toBeTruthy();
    expect(screen.getByRole("button", { name: /advanced metadata/i }).getAttribute("aria-expanded")).toBe("true");
  });

  it("changing the Title field calls onChange with just that field", () => {
    const onChange = vi.fn();
    render(<MetadataInput value={EMPTY} onChange={onChange} defaultOpen />);

    const title = screen.getByLabelText("Title") as HTMLInputElement;
    fireEvent.change(title, { target: { value: "new title" } });

    expect(onChange).toHaveBeenCalledWith({ title: "new title" });
  });

  it("trims whitespace on blur", () => {
    const onChange = vi.fn();
    render(<MetadataInput value={EMPTY} onChange={onChange} defaultOpen />);

    const title = screen.getByLabelText("Title") as HTMLInputElement;
    fireEvent.change(title, { target: { value: "  padded  " } });
    // Re-assert the value on blur: the component's `value` prop is static
    // in this test (onChange isn't wired back into it), so React resets the
    // DOM node after the change event's render — a real parent would instead
    // echo "  padded  " back through props, which is what this recreates.
    fireEvent.blur(title, { target: { value: "  padded  " } });

    expect(onChange).toHaveBeenLastCalledWith({ title: "padded" });
  });

  it("shows an inline error for an out-of-range year", () => {
    render(<MetadataInput value={{ ...EMPTY, year: "1899" }} onChange={vi.fn()} defaultOpen />);

    expect(screen.getByText(/enter a year between 1900 and 2100/i)).toBeTruthy();
    expect(screen.getByLabelText("Year").getAttribute("aria-invalid")).toBe("true");
  });

  it("clear all resets every field to empty", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <MetadataInput
        value={{ title: "T", authors: "A", venue: "V", year: "2020" }}
        onChange={onChange}
        defaultOpen
      />
    );

    await user.click(screen.getByText("Clear all"));

    expect(onChange).toHaveBeenCalledWith(EMPTY);
  });

  it("auto-fills empty fields from documentMetadata", () => {
    const onChange = vi.fn();
    render(
      <MetadataInput
        value={EMPTY}
        onChange={onChange}
        defaultOpen
        documentMetadata={{ title: "Doc Title", authors: "Doc Author", venue: "Doc Venue", year: "2021" }}
      />
    );

    expect(onChange).toHaveBeenCalledWith({
      title: "Doc Title",
      authors: "Doc Author",
      venue: "Doc Venue",
      year: "2021",
    });
  });

  it("does not overwrite fields the user already filled in", () => {
    const onChange = vi.fn();
    render(
      <MetadataInput
        value={{ title: "Kept", authors: "", venue: "", year: "" }}
        onChange={onChange}
        defaultOpen
        documentMetadata={{ title: "Doc Title", authors: "Doc Author" }}
      />
    );

    expect(onChange).toHaveBeenCalledWith({ authors: "Doc Author" });
  });
});
