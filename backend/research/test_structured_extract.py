"""Unit tests for W5 structured extract + W6 research job result storage."""

import json

from backend.research.jobs import RESULT_EVENT, store_research_job_result
from backend.research.structured_extract import (
    build_structured_extract_table,
    row_from_medical_understanding,
    table_prompt_block,
    table_to_csv,
    table_to_markdown,
)


SAMPLE_MEDICAL = {
    "populations": [{"description": "Adults with T2DM", "confidence": 0.8}],
    "interventions": [{"name": "metformin", "confidence": 0.9}],
    "comparators": [{"name": "placebo", "is_placebo": True}],
    "outcomes": [{"name": "HbA1c at 12 weeks"}],
    "key_findings": [{"statement": "Significant HbA1c reduction"}],
    "study_characteristics": {
        "study_design": "rct",
        "number_of_arms": 2,
        "blinding": "double-blind",
        "multicenter": True,
    },
}


def test_row_from_medical_understanding_fills_pico():
    row = row_from_medical_understanding(
        file_id=7,
        paper_title="Metformin RCT",
        paper_year="2020",
        medical=SAMPLE_MEDICAL,
        evidence_objects=[{"page": 4, "claim": "HbA1c dropped"}],
    )
    assert row["status"] == "ok"
    assert "T2DM" in row["population"]["value"]
    assert row["intervention"]["value"] == "metformin"
    assert row["comparator"]["value"] == "placebo"
    assert "HbA1c" in row["outcomes"]["value"]
    assert row["study_design"]["value"] == "rct"
    assert "double-blind" in row["methods"]["value"]
    assert "reduction" in row["key_findings"]["value"].lower()


def test_empty_medical_is_unknown_cells():
    row = row_from_medical_understanding(
        file_id=1,
        paper_title="Empty",
        medical={},
    )
    assert row["status"] == "empty"
    assert row["population"]["status"] == "unknown"


def test_table_exports_markdown_and_csv():
    table = build_structured_extract_table(
        project_id=3,
        papers=[
            {
                "file_id": 7,
                "paper_title": "Metformin RCT",
                "paper_year": "2020",
                "medical": SAMPLE_MEDICAL,
            }
        ],
    )
    assert table["metrics"]["filled_rows"] == 1
    md = table_to_markdown(table)
    assert "Population" in md
    assert "metformin" in md
    csv_body = table_to_csv(table)
    assert "population" in csv_body.splitlines()[0]
    assert "metformin" in csv_body
    block = table_prompt_block(table)
    assert "Structured extract table" in block
    assert "metformin" in block


def test_store_research_job_result_payload():
    added = []

    class FakeDB:
        def add(self, obj):
            added.append(obj)

        def commit(self):
            pass

    class FakeOutbox:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    store_research_job_result(
        FakeDB(),
        OutboxEvent=FakeOutbox,
        job_id=99,
        kind="theme_map",
        result={"kind": "theme_map", "themes": {"themes": []}},
    )
    assert added
    assert added[0].event_type == RESULT_EVENT
    assert added[0].status == "dispatched"
    payload = json.loads(added[0].payload)
    assert payload["kind"] == "theme_map"
    assert payload["result"]["kind"] == "theme_map"
