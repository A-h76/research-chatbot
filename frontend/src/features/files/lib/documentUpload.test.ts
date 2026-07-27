import { describe, it, expect } from "vitest";
import {
  MAX_LIBRARY_UPLOAD_FILES,
  partitionDocumentFiles,
} from "./documentUpload";

function f(name: string) {
  return new File(["x"], name);
}

describe("partitionDocumentFiles", () => {
  it("accepts pdf/epub/docx/txt and rejects others", () => {
    const { accepted, rejected } = partitionDocumentFiles([
      f("a.pdf"),
      f("b.PNG"),
      f("c.docx"),
      f("notes.txt"),
      f("book.epub"),
      f("slide.pptx"),
    ]);
    expect(accepted.map((x) => x.name)).toEqual([
      "a.pdf",
      "c.docx",
      "notes.txt",
      "book.epub",
    ]);
    expect(rejected.map((x) => x.name)).toEqual(["b.PNG", "slide.pptx"]);
  });

  it("exports a batch cap aligned with server default", () => {
    expect(MAX_LIBRARY_UPLOAD_FILES).toBe(50);
  });
});
