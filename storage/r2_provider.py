"""Cloudflare R2 (S3-compatible) object storage provider."""

import contextlib
import logging
import os
import tempfile

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from .provider import ObjectInfo, UploadPart


class R2Provider:
    supports_multipart = True

    def __init__(self, bucket: str, endpoint: str, access_key: str, secret_key: str):
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="auto",
        )

    def upload(self, key, local_path):
        self._client.upload_file(local_path, self.bucket, key)

    def delete(self, key):
        """Best-effort; missing objects / bucket hiccups must not block a DB
        row from being removed."""
        if not key:
            return
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            logging.exception("R2Provider.delete failed for key=%s", key)

    def head(self, key):
        try:
            resp = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return None
            raise
        return ObjectInfo(key=key, size=resp["ContentLength"], etag=resp.get("ETag", "").strip('"'))

    def list_keys(self, prefix=""):
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"]

    @contextlib.contextmanager
    def local_copy(self, key, suffix=""):
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            self._client.download_file(self.bucket, key, tmp)
            yield tmp
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    def presigned_get_url(self, key, filename, mime, expires_in=300):
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentType": mime or "application/octet-stream",
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=expires_in,
        )

    def presigned_put_url(self, key, mime, expires_in=600, content_md5_b64=None):
        params = {
            "Bucket": self.bucket,
            "Key": key,
            "ContentType": mime or "application/octet-stream",
        }
        if content_md5_b64:
            # R2/S3 reject the upload with 400 if the bytes it receives
            # don't hash to this — integrity is enforced *during* upload,
            # not just checked after the fact.
            params["ContentMD5"] = content_md5_b64
        return self._client.generate_presigned_url("put_object", Params=params, ExpiresIn=expires_in)

    def create_multipart_upload(self, key, mime):
        resp = self._client.create_multipart_upload(
            Bucket=self.bucket, Key=key, ContentType=mime or "application/octet-stream"
        )
        return resp["UploadId"]

    def presigned_part_url(self, key, upload_id, part_number, expires_in=3600):
        return self._client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
        )

    def complete_multipart_upload(self, key, upload_id, parts: list[UploadPart]):
        self._client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": [{"PartNumber": p.part_number, "ETag": p.etag} for p in parts]},
        )

    def abort_multipart_upload(self, key, upload_id):
        try:
            self._client.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
        except Exception:
            logging.exception(
                "R2Provider.abort_multipart_upload failed " "for key=%s upload_id=%s",
                key,
                upload_id,
            )
