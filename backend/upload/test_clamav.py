"""Unit tests for optional ClamAV scanning (PR3)."""

import pytest

from backend.upload.clamav import clamav_enabled, scan_bytes
from backend.upload.validation import ValidationError


def test_clamav_disabled_is_noop(monkeypatch):
    monkeypatch.delenv("CLAMAV_ENABLED", raising=False)
    assert not clamav_enabled()
    scan_bytes(b"%PDF-1.4", filename="a.pdf")  # must not raise


def test_clamav_enabled_unreachable_fails_closed(monkeypatch):
    monkeypatch.setenv("CLAMAV_ENABLED", "1")
    monkeypatch.setenv("CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("CLAMAV_PORT", "1")  # almost certainly closed
    monkeypatch.setenv("CLAMAV_TIMEOUT", "0.2")
    with pytest.raises(ValidationError) as exc:
        scan_bytes(b"%PDF-1.4", filename="a.pdf")
    assert exc.value.code == "clamav_unavailable"


def test_clamav_virus_response(monkeypatch):
    monkeypatch.setenv("CLAMAV_ENABLED", "1")

    def fake_instream(_data, environ=None):
        return "stream: Eicar-Test-Signature FOUND"

    monkeypatch.setattr("backend.upload.clamav._instream_scan", fake_instream)
    with pytest.raises(ValidationError) as exc:
        scan_bytes(b"X5O!P%@AP", filename="eicar.com")
    assert exc.value.code == "virus_detected"
