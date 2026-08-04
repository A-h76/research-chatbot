"""Unit tests for Dropbox connector (#27)."""

from __future__ import annotations

from backend.library import dropbox as mod


def test_dropbox_missing_env(monkeypatch):
    monkeypatch.delenv("DROPBOX_CLIENT_ID", raising=False)
    monkeypatch.delenv("DROPBOX_CLIENT_SECRET", raising=False)
    assert mod.dropbox_configured() is False
    assert len(mod.dropbox_missing_env()) >= 2


def test_dropbox_configured(monkeypatch):
    monkeypatch.setenv("DROPBOX_CLIENT_ID", "dbx-id")
    monkeypatch.setenv("DROPBOX_CLIENT_SECRET", "dbx-secret")
    assert mod.dropbox_configured() is True


def test_begin_oauth_includes_scopes(monkeypatch):
    monkeypatch.setenv("DROPBOX_CLIENT_ID", "dbx-id")
    monkeypatch.setenv("DROPBOX_CLIENT_SECRET", "dbx-secret")
    started = mod.begin_oauth("https://app.example/callback", "state123")
    url = started["authorize_url"]
    assert "dropbox.com/oauth2/authorize" in url
    assert "files.content.read" in url
    assert "state123" in url
    assert "dbx-id" in url


def test_oauth_redirect_uri_from_app_base(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://app.dhund.com/")
    assert mod.oauth_redirect_uri() == "https://app.dhund.com/api/library/dropbox/callback"


def test_list_pdf_files_parses_response(monkeypatch):
    def fake_post(path, token, body):
        assert path == "/files/list_folder"
        return {
            "entries": [
                {
                    ".tag": "file",
                    "id": "id:abc",
                    "name": "paper.pdf",
                    "size": 100,
                    "client_modified": "2024-01-01T00:00:00Z",
                },
                {".tag": "file", "id": "id:txt", "name": "notes.txt", "size": 10},
                {".tag": "folder", "id": "id:f", "name": "Research"},
            ],
            "has_more": False,
            "cursor": "",
        }

    monkeypatch.setattr(mod, "_api_post", fake_post)
    payload = mod.list_pdf_files("tok", folder_id="", limit=50)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "id:abc"
    assert payload["items"][0]["name"] == "paper.pdf"


def test_download_file_checks_magic(monkeypatch):
    class Resp:
        status_code = 200
        headers = {
            "Dropbox-API-Result": '{"name": "paper.pdf"}',
        }

        def iter_content(self, chunk_size=65536):
            yield b"%PDF-1.4 fake"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: Resp())
    hit = mod.download_file("tok", "id:abc")
    assert hit is not None
    data, name, ctype = hit
    assert data.startswith(b"%PDF")
    assert name.endswith(".pdf")
    assert ctype == "application/pdf"
