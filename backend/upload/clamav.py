"""Optional ClamAV (clamd) scanning for uploads (PR3).

Disabled by default (fail-open). When ``CLAMAV_ENABLED`` is truthy, scans
fail closed: virus → reject + quarantine; daemon unreachable → reject.
"""

from __future__ import annotations

import logging
import os
import socket
import struct
import uuid
from typing import Optional

from .errors import ValidationError

log = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on"}


def clamav_enabled(environ: Optional[dict] = None) -> bool:
    env = environ if environ is not None else os.environ
    return (env.get("CLAMAV_ENABLED") or "").strip().lower() in _TRUE


def _quarantine_dir(environ: Optional[dict] = None) -> str:
    env = environ if environ is not None else os.environ
    raw = (env.get("CLAMAV_QUARANTINE_DIR") or "").strip()
    if raw:
        return raw
    return os.path.join(os.environ.get("UPLOAD_DIR") or "uploads", "quarantine")


def quarantine_file(path: str, environ: Optional[dict] = None) -> str:
    """Move ``path`` into the quarantine directory; return destination path."""
    dest_dir = _quarantine_dir(environ)
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(path) or "upload"
    dest = os.path.join(dest_dir, f"{uuid.uuid4().hex}_{base}")
    try:
        os.replace(path, dest)
    except OSError:
        # Cross-device fallback
        import shutil

        shutil.copy2(path, dest)
        try:
            os.remove(path)
        except OSError:
            pass
    return dest


def _clamd_endpoint(environ: Optional[dict] = None) -> tuple[str, object]:
    env = environ if environ is not None else os.environ
    sock_path = (env.get("CLAMAV_SOCKET") or "").strip()
    if sock_path:
        return "unix", sock_path
    host = (env.get("CLAMAV_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    port = int(env.get("CLAMAV_PORT") or "3310")
    return "tcp", (host, port)


def _connect(environ: Optional[dict] = None) -> socket.socket:
    kind, endpoint = _clamd_endpoint(environ)
    if kind == "unix":
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(float((environ or os.environ).get("CLAMAV_TIMEOUT") or "10"))
        sock.connect(endpoint)  # type: ignore[arg-type]
        return sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float((environ or os.environ).get("CLAMAV_TIMEOUT") or "10"))
    sock.connect(endpoint)  # type: ignore[arg-type]
    return sock


def _instream_scan(data: bytes, environ: Optional[dict] = None) -> str:
    """Return clamd response line (e.g. ``stream: OK``)."""
    sock = _connect(environ)
    try:
        sock.sendall(b"zINSTREAM\0")
        # Chunk to avoid huge single writes
        view = memoryview(data)
        chunk = 64 * 1024
        for i in range(0, len(view), chunk):
            piece = view[i : i + chunk]
            sock.sendall(struct.pack(">I", len(piece)) + piece.tobytes())
        sock.sendall(struct.pack(">I", 0))
        resp = b""
        while True:
            more = sock.recv(4096)
            if not more:
                break
            resp += more
            if b"\0" in resp or b"\n" in resp:
                break
        return resp.decode("utf-8", errors="replace").strip().rstrip("\0")
    finally:
        try:
            sock.close()
        except OSError:
            pass


def scan_bytes(data: bytes, *, environ: Optional[dict] = None, filename: str = "") -> None:
    """Scan in-memory bytes. No-op when ClamAV is disabled."""
    if not clamav_enabled(environ):
        return
    try:
        result = _instream_scan(data, environ)
    except OSError as exc:
        log.error("clamav_unavailable filename=%s error=%s", filename, exc)
        raise ValidationError(
            "clamav_unavailable",
            "Virus scanner is enabled but unreachable; upload refused.",
        ) from exc

    upper = result.upper()
    if upper.endswith("OK") or " OK" in upper:
        return
    if "FOUND" in upper:
        raise ValidationError(
            "virus_detected",
            f"File failed virus scan ({result}).",
        )
    raise ValidationError(
        "clamav_unavailable",
        f"Virus scanner returned an error ({result}).",
    )


def scan_path(path: str, *, environ: Optional[dict] = None, filename: str = "") -> None:
    """Scan a local file path. Quarantines on virus when possible."""
    if not clamav_enabled(environ):
        return
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        scan_bytes(data, environ=environ, filename=filename or path)
    except ValidationError as exc:
        if exc.code == "virus_detected":
            try:
                qpath = quarantine_file(path, environ)
                log.warning(
                    "event=virus_detected quarantined=%s filename=%s",
                    qpath,
                    filename or path,
                )
            except OSError:
                log.exception("quarantine failed for %s", path)
        raise
