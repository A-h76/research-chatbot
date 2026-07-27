// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { LibraryUploadZone } from "./LibraryUploadZone";

afterEach(() => cleanup());

describe("LibraryUploadZone", () => {
  it("renders the upload affordance and accepts document files via the hidden input", () => {
    const onFiles = vi.fn();
    render(<LibraryUploadZone onFiles={onFiles} />);

    expect(screen.getByText(/Drop papers here/i)).toBeTruthy();
    const input = document.getElementById("library-upload-input") as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.accept).toContain(".pdf");
    expect(input.multiple).toBe(true);

    const file = new File(["%PDF"], "paper.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFiles).toHaveBeenCalledTimes(1);
    const arg = onFiles.mock.calls[0]![0] as FileList | File[];
    expect(Array.from(arg as FileList)[0]?.name ?? (arg as File[])[0]?.name).toBe("paper.pdf");
  });

  it("does not open the picker when disabled", () => {
    const onFiles = vi.fn();
    render(<LibraryUploadZone onFiles={onFiles} disabled />);
    const input = document.getElementById("library-upload-input") as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });
});
