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
    assert by_id["pubmed"]["availability"] == "live"
    assert by_id["pubmed"]["status"] == "Live"
    # ORCID must never appear as Live until wired
    assert by_id["orcid"]["availability"] == "live"
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
    assert by_id["pubmed"]["connection_state"] == "n/a"
    assert by_id["writing_studio"]["connection_state"] in {"n/a", "coming_soon"}
    # Live first-party / scholarly without OAuth
    if by_id["openalex"]["availability"] == "live":
        assert by_id["openalex"]["connection_state"] == "n/a"


def test_no_fake_live_for_unwired_cloud():
    data = public_catalog()
    for pid in ("box",):
        p = next(x for x in data["providers"] if x["id"] == pid)
        assert p["availability"] == "soon"


def test_dropbox_provider_def_is_live_connectable():
    dbx = next(p for p in PROVIDER_DEFS if p["id"] == "dropbox")
    assert dbx["availability"] == "live"
    assert dbx["connectable"] is True
    assert dbx["capabilities"]["import"] is True
    assert dbx["capabilities"]["folder_watch"] is False
    assert dbx["actions"]["connect"]["path"] == "/api/library/dropbox/connect"
    assert "dropbox" in dbx["actions"]["deep_link"]


def test_onedrive_provider_def_is_live_connectable():
    od = next(p for p in PROVIDER_DEFS if p["id"] == "onedrive")
    assert od["availability"] == "live"
    assert od["connectable"] is True
    assert od["capabilities"]["import"] is True
    assert od["capabilities"]["folder_watch"] is False
    assert od["actions"]["connect"]["path"] == "/api/library/onedrive/connect"
    assert "onedrive" in od["actions"]["deep_link"]


def test_arxiv_provider_def_is_live():
    ax = next(p for p in PROVIDER_DEFS if p["id"] == "arxiv")
    assert ax["availability"] == "live"
    assert ax["capabilities"]["import"] is True
    assert "arxiv" in ax["actions"]["deep_link"]


def test_europe_pmc_provider_def_is_live():
    ep = next(p for p in PROVIDER_DEFS if p["id"] == "europe_pmc")
    assert ep["availability"] == "live"
    assert ep["capabilities"]["import"] is True
    assert "europe_pmc" in ep["actions"]["deep_link"]


def test_orcid_provider_def_is_live():
    od = next(p for p in PROVIDER_DEFS if p["id"] == "orcid")
    assert od["availability"] == "live"
    assert od["auth"] == "none"
    assert od["capabilities"]["import"] is True
    assert "orcid" in od["actions"]["deep_link"]


def test_google_drive_provider_def_is_live_connectable():
    """Catalog + public landing show live; Settings still reports server_configured."""
    gd = next(p for p in PROVIDER_DEFS if p["id"] == "google_drive")
    assert gd["availability"] == "live"
    assert gd["connectable"] is True
    assert gd["capabilities"]["import"] is True
    assert gd["capabilities"]["folder_watch"] is False
    assert gd["actions"]["connect"]["path"] == "/api/library/google_drive/connect"
    assert "google_drive" in gd["actions"]["deep_link"]
    pub = {p["id"]: p for p in public_catalog()["providers"]}
    assert pub["google_drive"]["availability"] == "live"
    assert pub["dropbox"]["availability"] == "live"
    assert pub["onedrive"]["availability"] == "live"
