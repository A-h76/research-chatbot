"""Unit tests for Google Drive connector (#23)."""

from __future__ import annotations

from backend.library import google_drive as mod


def test_drive_missing_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    assert mod.drive_configured() is False
    assert len(mod.drive_missing_env()) >= 2


def test_drive_configured_falls_back_to_google_client(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gsecret")
    assert mod.drive_configured() is True


def test_begin_oauth_includes_drive_scope(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "drive-id")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "drive-secret")
    started = mod.begin_oauth("https://app.example/callback", "state123")
    url = started["authorize_url"]
    assert "accounts.google.com" in url
    assert "drive.readonly" in url
    assert "state123" in url
    assert "drive-id" in url


def test_oauth_redirect_uri_from_app_base(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://app.dhund.com/")
    assert mod.oauth_redirect_uri() == "https://app.dhund.com/api/library/google_drive/callback"
    assert (
        mod.oauth_redirect_uri("https://localhost:5000")
        == "https://localhost:5000/api/library/google_drive/callback"
    )


def test_list_pdf_files_parses_response(monkeypatch):
    def fake_get(path, token, *, params=None):
        assert path == "/files"
        return {
            "files": [
                {
                    "id": "abc",
                    "name": "Paper.pdf",
                    "mimeType": "application/pdf",
                    "size": "1024",
                    "modifiedTime": "2024-01-01T00:00:00.000Z",
                    "webViewLink": "https://drive.google.com/file/d/abc",
                }
            ],
            "nextPageToken": "",
        }

    monkeypatch.setattr(mod, "_api_get", fake_get)
    out = mod.list_pdf_files("tok", folder_id="root", limit=10)
    assert len(out["items"]) == 1
    assert out["items"][0]["id"] == "abc"
    assert out["items"][0]["name"] == "Paper.pdf"


def test_download_file_rejects_non_pdf(monkeypatch):
    def fake_get(path, token, *, params=None):
        return {"id": "x", "name": "doc.docx", "mimeType": "application/msword", "size": "10"}

    monkeypatch.setattr(mod, "_api_get", fake_get)
    assert mod.download_file("tok", "x") is None


def test_adapter_import_files(monkeypatch):
    from backend.library.adapters.google_drive_adapter import GoogleDriveAdapter

    monkeypatch.setattr(
        mod,
        "download_file",
        lambda token, fid, *, max_bytes=0: (b"%PDF-1.4", "a.pdf", "application/pdf"),
    )
    adapter = GoogleDriveAdapter()
    result = adapter.import_files(access_token="t", item_keys=["f1"], max_bytes=1000)
    assert len(result["downloaded"]) == 1
    assert result["downloaded"][0]["filename"] == "a.pdf"
