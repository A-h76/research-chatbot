"""Unit tests for OneDrive connector (#28)."""

from __future__ import annotations

from backend.library import onedrive as mod


def test_onedrive_missing_env(monkeypatch):
    for name in (
        "ONEDRIVE_CLIENT_ID",
        "ONEDRIVE_CLIENT_SECRET",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    assert mod.onedrive_configured() is False
    assert len(mod.onedrive_missing_env()) >= 2


def test_onedrive_configured(monkeypatch):
    monkeypatch.setenv("ONEDRIVE_CLIENT_ID", "od-id")
    monkeypatch.setenv("ONEDRIVE_CLIENT_SECRET", "od-secret")
    assert mod.onedrive_configured() is True


def test_onedrive_configured_via_microsoft_alias(monkeypatch):
    for name in ("ONEDRIVE_CLIENT_ID", "ONEDRIVE_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "ms-id")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "ms-secret")
    assert mod.onedrive_configured() is True


def test_begin_oauth_includes_scopes(monkeypatch):
    monkeypatch.setenv("ONEDRIVE_CLIENT_ID", "od-id")
    monkeypatch.setenv("ONEDRIVE_CLIENT_SECRET", "od-secret")
    started = mod.begin_oauth("https://app.example/callback", "state123")
    url = started["authorize_url"]
    assert "login.microsoftonline.com" in url
    assert "Files.Read" in url
    assert "state123" in url
    assert "od-id" in url


def test_oauth_redirect_uri_from_app_base(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://app.dhund.com/")
    assert mod.oauth_redirect_uri() == "https://app.dhund.com/api/library/onedrive/callback"


def test_list_pdf_files_parses_response(monkeypatch):
    def fake_get(path, token, *, params=None):
        assert "/me/drive/root/children" in path
        return {
            "value": [
                {
                    "id": "item-pdf",
                    "name": "paper.pdf",
                    "size": 100,
                    "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                    "webUrl": "https://onedrive.example/paper.pdf",
                    "file": {"mimeType": "application/pdf"},
                },
                {
                    "id": "item-txt",
                    "name": "notes.txt",
                    "size": 10,
                    "file": {"mimeType": "text/plain"},
                },
                {
                    "id": "item-folder",
                    "name": "Research",
                    "folder": {"childCount": 2},
                },
            ]
        }

    monkeypatch.setattr(mod, "_api_get", fake_get)
    payload = mod.list_pdf_files("tok", folder_id="root", limit=50)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "item-pdf"
    assert payload["items"][0]["name"] == "paper.pdf"


def test_download_file_checks_magic(monkeypatch):
    monkeypatch.setattr(
        mod,
        "_api_get",
        lambda path, token, *, params=None: {
            "id": "item-1",
            "name": "paper.pdf",
            "size": 12,
            "file": {"mimeType": "application/pdf"},
        },
    )

    class Resp:
        status_code = 200

        def iter_content(self, chunk_size=65536):
            yield b"%PDF-1.4 fake"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: Resp())
    hit = mod.download_file("tok", "item-1")
    assert hit is not None
    data, name, ctype = hit
    assert data.startswith(b"%PDF")
    assert name.endswith(".pdf")
    assert ctype == "application/pdf"
