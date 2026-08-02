"""Integrations catalog — single source of truth (#11)."""

from __future__ import annotations

from backend.ecosystem.catalog import (
    CATEGORIES,
    PROVIDER_DEFS,
    build_catalog,
    public_catalog,
)


def test_categories_match_masterplan():
    ids = [c[0] for c in CATEGORIES]
    assert ids == [
        "reference_managers",
        "academic_sources",
        "cloud_storage",
        "writing",
        "ai",
        "developer",
        "identity",
    ]


def test_public_catalog_honest_statuses():
    data = public_catalog()
    by_id = {p["id"]: p for p in data["providers"]}
    assert "zotero" in by_id
    assert "mendeley" in by_id
    assert "pubmed" in by_id
    assert by_id["pubmed"]["availability"] == "soon"
    assert by_id["pubmed"]["status"] == "Coming Soon"
    # ORCID must never appear as Live until wired
    assert by_id["orcid"]["availability"] == "soon"
    assert by_id["open_api"]["availability"] == "soon"
    # Every provider has the contract fields
    for p in data["providers"]:
        assert "capabilities" in p
        assert "auth" in p
        assert set(p["capabilities"]) >= {
            "import",
            "sync",
            "pdf_pull",
            "folder_watch",
            "write_back",
        }


def test_zotero_capabilities_when_live():
    z = next(p for p in PROVIDER_DEFS if p["id"] == "zotero")
    assert z["capabilities"]["import"] is True
    assert z["capabilities"]["sync"] is True
    assert z["capabilities"]["pdf_pull"] is True
    assert z["connectable"] is True


def test_build_catalog_connection_states():
    data = build_catalog(user_id=None)
    by_id = {p["id"]: p for p in data["providers"]}
    assert by_id["pubmed"]["connection_state"] == "coming_soon"
    assert by_id["writing_studio"]["connection_state"] in {"n/a", "coming_soon"}
    # Live first-party / scholarly without OAuth
    if by_id["openalex"]["availability"] == "live":
        assert by_id["openalex"]["connection_state"] == "n/a"


def test_no_fake_live_for_unwired_cloud():
    data = public_catalog()
    for pid in ("google_drive", "dropbox", "onedrive", "box"):
        p = next(x for x in data["providers"] if x["id"] == pid)
        assert p["availability"] == "soon"
