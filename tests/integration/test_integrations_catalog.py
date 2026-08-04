"""HTTP smoke for integrations catalog API (#11)."""

from __future__ import annotations


def test_public_catalog_endpoint(client):
    r = client.get("/api/integrations/catalog/public")
    assert r.status_code == 200
    data = r.get_json()
    assert "categories" in data and "providers" in data
    ids = {p["id"] for p in data["providers"]}
    assert "zotero" in ids and "pubmed" in ids and "orcid" in ids
    orcid = next(p for p in data["providers"] if p["id"] == "orcid")
    assert orcid["availability"] == "live"


def test_authed_catalog_endpoint(researcher):
    r = researcher.client.get("/api/integrations/catalog")
    assert r.status_code == 200
    data = r.get_json()
    assert data["providers"]
    z = next(p for p in data["providers"] if p["id"] == "zotero")
    assert "connection_state" in z
    assert "capabilities" in z
    assert "actions" in z
