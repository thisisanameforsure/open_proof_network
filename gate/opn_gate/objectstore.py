"""The ``ObjectStore`` seam (conventions §1): where the olean cache lives (F10-R7; C8 item 4).

Three implementations of one protocol. ``HttpStore`` reads a public bucket through its
CloudFront URL with the standard library and cannot write, which is every consumer's view of
the cache: ``pregate.sh``, the devcontainer and CI fetch, nobody else uploads. ``S3Store`` writes
through boto3 with whatever credentials the environment carries — in the post-merge job, the
OIDC role the site stack grants the graph repository's ``main`` (C8 item 4), never a stored
key. ``MemoryStore`` is the fake the tests drive.

Keys are ``<target>/<commit>/manifest.json``, ``<target>/<commit>/oleans.tar.gz`` and
``<target>/index.json`` (``opn_gate.cache``); a store neither knows nor cares.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

TIMEOUT_S = 60
MAX_OBJECT_BYTES = 512 * 1024 * 1024  # a cache archive well past §6's 50 MiB is refused unread


class ObjectStoreError(RuntimeError):
    """The store could not answer (network, credentials, a refused write)."""


class ObjectStore(Protocol):
    def get(self, key: str) -> bytes | None:
        """The object's bytes, or ``None`` when there is no such key."""

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        """Write the object; ``ObjectStoreError`` when the store refuses."""


class HttpStore:
    """A public-read store behind an https URL (the CloudFront front of the cache bucket)."""

    def __init__(self, base_url: str, *, opener: Any | None = None) -> None:
        if not base_url.startswith("https://"):
            msg = f"the cache is fetched over https only: {base_url}"
            raise ObjectStoreError(msg)
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urllib.request.urlopen

    def get(self, key: str) -> bytes | None:
        request = urllib.request.Request(  # noqa: S310 — https enforced above
            f"{self.base_url}/{key}", headers={"User-Agent": "opn-gate-cache"}
        )
        try:
            with self.opener(request, timeout=TIMEOUT_S) as resp:
                length = int(resp.headers.get("Content-Length") or 0)
                if length > MAX_OBJECT_BYTES:
                    msg = f"{key} is {length} bytes; refusing to read more than {MAX_OBJECT_BYTES}"
                    raise ObjectStoreError(msg)
                data: bytes = resp.read(MAX_OBJECT_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):  # CloudFront answers 403 for a missing S3 object
                return None
            msg = f"GET {key}: HTTP {exc.code}"
            raise ObjectStoreError(msg) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            msg = f"GET {key}: {exc}"
            raise ObjectStoreError(msg) from exc
        if len(data) > MAX_OBJECT_BYTES:
            msg = f"{key} exceeds {MAX_OBJECT_BYTES} bytes"
            raise ObjectStoreError(msg)
        return data

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        msg = "the https view of the cache is read-only; uploads go through S3Store"
        raise ObjectStoreError(msg)


class S3Store:
    """The bucket itself, for the post-merge job's uploads. boto3 is imported lazily: it is a
    dev-group dependency here and present in the Lambda runtime (F05 §8), never needed by a
    prover's laptop."""

    def __init__(self, bucket: str, *, prefix: str = "", client: Any | None = None) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if client is None:
            import boto3  # noqa: PLC0415 — only the uploading side needs it

            client = boto3.client("s3")
        self.client = client

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def get(self, key: str) -> bytes | None:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:  # botocore's error classes are dynamic
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return None
            msg = f"GET s3://{self.bucket}/{self._key(key)}: {exc}"
            raise ObjectStoreError(msg) from exc
        data: bytes = obj["Body"].read()
        return data

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=self._key(key), Body=data, ContentType=content_type
            )
        except Exception as exc:
            msg = f"PUT s3://{self.bucket}/{self._key(key)}: {exc}"
            raise ObjectStoreError(msg) from exc


@dataclass
class MemoryStore:
    """The fake: a dict, plus a switch that makes every call fail (C7's outage path)."""

    objects: dict[str, bytes] = field(default_factory=dict)
    unreachable: bool = False
    reads: list[str] = field(default_factory=list)

    def get(self, key: str) -> bytes | None:
        self.reads.append(key)
        if self.unreachable:
            msg = f"GET {key}: simulated outage"
            raise ObjectStoreError(msg)
        return self.objects.get(key)

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        if self.unreachable:
            msg = f"PUT {key}: simulated outage"
            raise ObjectStoreError(msg)
        self.objects[key] = bytes(data)
