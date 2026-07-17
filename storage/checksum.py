"""Streaming file hashes — never load a whole upload into memory to hash it."""
import base64
import hashlib

_CHUNK = 1024 * 1024


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file_b64(path: str) -> str:
    """Base64 MD5, the form S3/R2 `Content-MD5` expects for upload integrity."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode()
