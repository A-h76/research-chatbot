"""S3Backend — for future standard-AWS-S3 compatibility. Reuses
storage/r2_provider.py's R2Provider outright rather than writing a
second boto3 wrapper: R2Provider is already a generic S3-compatible
client (bucket/endpoint/keys passed in at construction, no R2-specific
API calls anywhere in it) — R2 is just what its constructor defaults
point at. Passing a standard AWS endpoint (or none, letting boto3 use
its own AWS default) makes the exact same class talk to real S3.
"""
import os
from typing import BinaryIO, Optional

from storage.r2_provider import R2Provider

from .r2 import R2Backend


def _s3_config_from_env():
    return dict(
        bucket=os.environ.get("AWS_S3_BUCKET", ""),
        # None (not an R2-style forced endpoint) — boto3 resolves the
        # correct regional AWS S3 endpoint on its own from the region.
        endpoint=os.environ.get("AWS_S3_ENDPOINT") or
                f"https://s3.{os.environ.get('AWS_REGION', 'us-east-1')}.amazonaws.com",
        access_key=os.environ.get("AWS_ACCESS_KEY_ID", ""),
        secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    )


class S3Backend(R2Backend):
    """Identical behavior to R2Backend — the only difference is which
    env vars configure the underlying R2Provider instance."""
    def __init__(self, provider: Optional[R2Provider] = None):
        super().__init__(provider or R2Provider(**_s3_config_from_env()))
