import sys
from pathlib import Path

from backend.document_understanding.pipeline import DocumentUnderstandingPipeline

# Windows consoles default to cp1252, which can't encode ligatures (e.g.
# "ﬁ") that real academic PDFs commonly contain in their extracted text —
# without this, printing such a document's abstract/full text crashes.
sys.stdout.reconfigure(encoding="utf-8")


def enum_value(value):
    """Return Enum.value if this is an Enum, otherwise return as-is."""
    return getattr(value, "value", value)


def main():
    default_pdf = Path(r"D:\chatbot (v1)\testPDF\sample_papers\testingSmpl.pdf")
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else default_pdf

    if not pdf.exists():
        print(f"❌ PDF not found:\n{pdf}")
        return

    print("=" * 90)
    print("PHASE 1.1 - DOCUMENT UNDERSTANDING PIPELINE")
    print("=" * 90)
    print(f"PDF: {pdf}")
    print()

    pipeline = DocumentUnderstandingPipeline()

    try:
        doc = pipeline.process(pdf)
    except Exception:
        print("\n❌ Pipeline crashed.\n")
        raise

    md = doc.metadata
    st = doc.statistics
    q = doc.quality

    print("=" * 90)
    print("DOCUMENT INFORMATION")
    print("=" * 90)

    print(f"ID                 : {doc.id}")
    print(f"Pipeline Version   : {doc.pipeline_version}")
    print(f"Schema Version     : {doc.schema_version}")
    print(f"Processing Time    : {doc.processing_time_ms:.2f} ms")
    print(f"Created At         : {doc.created_at}")

    print()

    print("=" * 90)
    print("METADATA")
    print("=" * 90)

    print(f"Title              : {md.title}")
    print(f"Subtitle           : {md.subtitle}")
    print(f"Authors            : {md.authors}")
    print(f"Affiliations       : {md.affiliations}")
    print(f"Corresponding      : {md.corresponding_author}")
    print(f"Venue              : {md.venue}")
    print(f"Journal            : {md.journal}")
    print(f"Conference         : {md.conference}")
    print(f"Publication Year   : {md.publication_year}")
    print(f"DOI                : {md.doi}")
    print(f"PMID               : {md.pmid}")
    print(f"PMCID              : {md.pmcid}")
    print(f"ArXiv ID           : {md.arxiv_id}")
    print(f"ClinicalTrials ID  : {md.clinical_trials_id}")
    print(f"Language           : {enum_value(md.language)}")
    print(f"License            : {md.license}")

    print("\nKeywords")
    print("-" * 90)
    print(md.keywords)

    print("\nAbstract")
    print("-" * 90)
    print(md.abstract)

    print()

    print("=" * 90)
    print("DOCUMENT STATISTICS")
    print("=" * 90)

    print(f"Pages              : {st.page_count}")
    print(f"Words              : {st.word_count}")
    print(f"Characters         : {st.char_count}")
    print(f"Reading Time       : {st.estimated_reading_time_minutes}")
    print(f"References         : {st.reference_count}")
    print(f"Figures            : {st.figure_count}")
    print(f"Tables             : {st.table_count}")
    print(f"Headings           : {st.heading_count}")
    print(f"Sections           : {st.section_count}")

    print()

    print("=" * 90)
    print("QUALITY ASSESSMENT")
    print("=" * 90)

    print(f"OCR Quality        : {enum_value(q.ocr_quality)}")
    print(f"Metadata Quality   : {enum_value(q.metadata_quality)}")
    print(f"Section Quality    : {enum_value(q.section_quality)}")
    print(f"Extraction Quality : {enum_value(q.extraction_quality)}")
    print(f"Layout Quality     : {enum_value(q.layout_quality)}")
    print(f"Completeness       : {q.completeness}")
    print(f"Confidence         : {q.confidence}")

    print("\nWarnings")
    print("-" * 90)

    if q.warnings:
        for warning in q.warnings:
            print(f"• {warning}")
    else:
        print("None")

    print("\nErrors")
    print("-" * 90)

    if q.errors:
        for error in q.errors:
            print(f"• {error}")
    else:
        print("None")

    print()

    print("=" * 90)
    print("SECTION OVERVIEW")
    print("=" * 90)

    if doc.structure.raw_headings:
        for section in doc.structure.raw_headings:
            print(f"• {section}")
    else:
        print("No sections detected.")

    print()

    print("=" * 90)
    print("NORMALIZED HEADINGS")
    print("=" * 90)

    if doc.structure.normalized_headings:
        for heading in doc.structure.normalized_headings:
            print(f"• {enum_value(heading)}")
    else:
        print("No headings detected.")

    print()

    print("=" * 90)
    print("SECTION PREVIEW")
    print("=" * 90)

    if doc.structure.raw_headings:
        for name, text in doc.structure.raw_headings.items():

            print(f"\n{name.upper()}")
            print("-" * 90)

            preview = text[:500]

            print(preview)

            if len(text) > 500:
                print("\n... (truncated)")
    else:
        print("No section content available.")

    print()

    print("=" * 90)
    print("TRACEABILITY")
    print("=" * 90)

    print(f"Total Entries: {len(doc.traceability)}")

    if doc.traceability:
        for key, ref in list(doc.traceability.items())[:10]:

            print()

            print(f"Key: {key}")
            print(ref)
    else:
        print("No traceability entries.")

    print()

    print("=" * 90)
    print("PIPELINE STAGES")
    print("=" * 90)

    for stage in doc.stage_logs:

        print(
            f"{stage.stage:<15}"
            f"{enum_value(stage.status):<12}"
            f"{stage.duration_ms:>8.1f} ms"
        )

        if stage.confidence is not None:
            print(f"   Confidence : {stage.confidence}")

        if stage.warnings:
            print("   Warnings")
            for warning in stage.warnings:
                print(f"      • {warning}")

        if stage.errors:
            print("   Errors")
            for error in stage.errors:
                print(f"      • {error}")

    print()

    print("=" * 90)
    print("FULL TEXT PREVIEW")
    print("=" * 90)

    print(doc.full_text[:1000])

    if len(doc.full_text) > 1000:
        print("\n... (truncated) ...")

    print()

    print("=" * 90)
    print("PROCESSING SUMMARY")
    print("=" * 90)

    print(f"Title Found            : {bool(md.title)}")
    print(f"Abstract Found         : {bool(md.abstract)}")
    print(f"Authors Found          : {len(md.authors)}")
    print(f"Language Detected      : {enum_value(md.language)}")
    print(f"Sections Detected      : {st.section_count}")
    print(f"Headings Detected      : {st.heading_count}")
    print(f"Traceability Entries   : {len(doc.traceability)}")
    print(f"Warnings               : {len(q.warnings)}")
    print(f"Errors                 : {len(q.errors)}")
    print(f"Overall Confidence     : {q.confidence}")

    print()

    if len(q.errors) == 0:
        print("✅ Phase 1.1 completed successfully.")
    else:
        print("⚠️ Phase 1.1 completed with errors.")

    print("=" * 90)


if __name__ == "__main__":
    main()