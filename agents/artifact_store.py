"""MinIO Artifact Store — upload, presigned URLs, public URLs.

Stores Plotly HTML/PNG/CSV chart artifacts in MinIO (S3-compatible).
Exposes presigned URLs for secure time-limited access and public URLs
for buckets configured with public-read policy.

Configuration (env vars):
    MINIO_ENDPOINT      — host:port (default: localhost:9000)
    MINIO_ACCESS_KEY    — access key (default: minioadmin)
    MINIO_SECRET_KEY    — secret key (default: minioadmin)
    MINIO_BUCKET        — bucket name (default: aria-artifacts)
    MINIO_SECURE        — use TLS (default: false)
    MINIO_REGION        — region name (default: us-east-1)

Usage:
    from agents.artifact_store import ArtifactStore, ArtifactRef

    store = ArtifactStore()
    ref = store.upload_html("<html>...</html>", key="conv_42/chart_001")
    print(ref.presigned_url(expires=3600))
"""

from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from minio import Minio  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from agents.chart_renderer import RenderOutput

log = structlog.get_logger(__name__)


# ── Configuration ───────────────────────────────────────────────────────────


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# ── Artifact reference ──────────────────────────────────────────────────────


@dataclass
class ArtifactRef:
    """Reference to a stored artifact in MinIO."""

    key: str
    """Object key within the bucket."""

    bucket: str
    """Bucket name."""

    format: str
    """Artifact format: html, png, csv, json."""

    size_bytes: int
    """Size of the artifact in bytes."""

    content_type: str
    """HTTP Content-Type header value."""

    created_at: str
    """ISO 8601 timestamp of upload."""

    etag: str = ""
    """S3 ETag of the uploaded object (for integrity checks)."""

    _store: ArtifactStore | None = field(default=None, repr=False)
    """Back-reference to the store for URL generation."""

    def presigned_url(self, expires: int = 3600) -> str:
        """Generate a presigned GET URL with expiry in seconds.

        Args:
            expires: URL lifetime in seconds (default: 1 hour).

        Returns:
            Full presigned URL, or empty string if store not available.
        """
        if self._store is None:
            return ""
        return self._store.presigned_url(self.key, expires_seconds=expires)

    def public_url(self) -> str:
        """Generate the public S3 URL for this artifact.

        Only works if the bucket or object has public-read ACL/policy.
        """
        if self._store is None:
            return ""
        return self._store.public_url(self.key)

    def delete(self) -> bool:
        """Delete this artifact from the store."""
        if self._store is None:
            return False
        return self._store.delete(self.key)


# ── Content type map ────────────────────────────────────────────────────────

_CONTENT_TYPES: dict[str, str] = {
    "html": "text/html; charset=utf-8",
    "png": "image/png",
    "csv": "text/csv; charset=utf-8",
    "json": "application/json; charset=utf-8",
}


def _ext_to_format(ext: str) -> str:
    """Map file extension to artifact format name."""
    ext = ext.lower().lstrip(".")
    return {"html": "html", "htm": "html", "png": "png", "csv": "csv", "json": "json"}.get(ext, ext)


# ── Artifact Store ──────────────────────────────────────────────────────────


class ArtifactStore:
    """MinIO-backed artifact store for chart outputs.

    Thread-safe. Call ``connect()`` explicitly or let lazy init handle it.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
        region: str | None = None,
    ) -> None:
        """Initialise the store (does not connect until first use).

        Args:
            endpoint: MinIO endpoint (host:port). Default from MINIO_ENDPOINT.
            access_key: Access key. Default from MINIO_ACCESS_KEY.
            secret_key: Secret key. Default from MINIO_SECRET_KEY.
            bucket: Bucket name. Default from MINIO_BUCKET.
            secure: Use TLS. Default from MINIO_SECURE.
            region: Region name. Default from MINIO_REGION.
        """
        self._endpoint = endpoint or _env("MINIO_ENDPOINT", "localhost:9000")
        self._access_key = access_key or _env("MINIO_ACCESS_KEY", "minioadmin")
        self._secret_key = secret_key or _env("MINIO_SECRET_KEY", "minioadmin")
        self._bucket = bucket or _env("MINIO_BUCKET", "aria-artifacts")
        self._secure = secure if secure is not None else _env_bool("MINIO_SECURE", False)
        self._region = region or _env("MINIO_REGION", "us-east-1")
        self._client: Minio | None = None

    # ── Connection management ────────────────────────────────────────────

    @property
    def client(self) -> Minio:
        """Lazy-init MinIO client."""
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    def connect(self) -> Minio:
        """Create and return the MinIO client, ensuring the bucket exists."""
        self._client = Minio(
            endpoint=self._endpoint,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=self._secure,
            region=self._region,
        )
        self._ensure_bucket()
        log.info(
            "artifact_store.connected",
            endpoint=self._endpoint,
            bucket=self._bucket,
            secure=self._secure,
        )
        return self._client

    def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        assert self._client is not None
        try:
            if not self._client.bucket_exists(self._bucket):
                # minio SDK's make_bucket takes `location`, NOT `region` (only the
                # Minio(...) constructor takes `region`). Passing `region` raises a
                # TypeError that `except S3Error` won't catch, killing the upload.
                self._client.make_bucket(self._bucket, location=self._region)
                log.info("artifact_store.bucket_created", bucket=self._bucket)
        except S3Error as exc:
            log.warning("artifact_store.bucket_check_failed", error=str(exc))

    # ── Upload methods ───────────────────────────────────────────────────

    def upload_html(
        self,
        content: str,
        *,
        key: str | None = None,
        key_prefix: str = "artifacts",
    ) -> ArtifactRef:
        """Upload HTML content to MinIO.

        Args:
            content: HTML string.
            key: Object key (auto-generated if None).
            key_prefix: Prefix for auto-generated keys.

        Returns:
            ArtifactRef with key, size, content_type.
        """
        if key is None:
            key = f"{key_prefix.rstrip('/')}/{uuid.uuid4().hex}.html"
        return self._upload(
            content.encode("utf-8"),
            key=key,
            format="html",
            content_type="text/html; charset=utf-8",
        )

    def upload_png(
        self,
        content: bytes,
        *,
        key: str | None = None,
        key_prefix: str = "artifacts",
    ) -> ArtifactRef:
        """Upload PNG image content to MinIO.

        Args:
            content: PNG image bytes.
            key: Object key (auto-generated if None).
            key_prefix: Prefix for auto-generated keys.

        Returns:
            ArtifactRef with key, size, content_type.
        """
        if key is None:
            key = f"{key_prefix.rstrip('/')}/{uuid.uuid4().hex}.png"
        return self._upload(
            content,
            key=key,
            format="png",
            content_type="image/png",
        )

    def upload_csv(
        self,
        content: str,
        *,
        key: str | None = None,
        key_prefix: str = "artifacts",
    ) -> ArtifactRef:
        """Upload CSV content to MinIO.

        Args:
            content: CSV string.
            key: Object key (auto-generated if None).
            key_prefix: Prefix for auto-generated keys.

        Returns:
            ArtifactRef with key, size, content_type.
        """
        if key is None:
            key = f"{key_prefix.rstrip('/')}/{uuid.uuid4().hex}.csv"
        return self._upload(
            content.encode("utf-8"),
            key=key,
            format="csv",
            content_type="text/csv; charset=utf-8",
        )

    def upload_json(
        self,
        content: str,
        *,
        key: str | None = None,
        key_prefix: str = "vault",
    ) -> ArtifactRef:
        """Upload JSON content to MinIO (for vault archives).

        Args:
            content: JSON string.
            key: Object key (auto-generated if None).
            key_prefix: Prefix for auto-generated keys.

        Returns:
            ArtifactRef with key, size, content_type.
        """
        if key is None:
            key = f"{key_prefix.rstrip('/')}/{uuid.uuid4().hex}.json"
        return self._upload(
            content.encode("utf-8"),
            key=key,
            format="json",
            content_type="application/json; charset=utf-8",
        )

    def upload_file(
        self,
        path: str | Path,
        *,
        key: str | None = None,
        key_prefix: str = "artifacts",
    ) -> ArtifactRef:
        """Upload a local file to MinIO.

        Args:
            path: Path to local file.
            key: Object key (derived from filename if None).
            key_prefix: Prefix for auto-generated keys.

        Returns:
            ArtifactRef with key, size, content_type.
        """
        path = Path(path)
        if key is None:
            key = f"{key_prefix.rstrip('/')}/{path.name}"
        content = path.read_bytes()
        ext = path.suffix
        fmt = _ext_to_format(ext)
        ct = _CONTENT_TYPES.get(fmt, "application/octet-stream")
        return self._upload(content, key=key, format=fmt, content_type=ct)

    def upload_from_render_output(
        self,
        output: RenderOutput,
        *,
        key_prefix: str = "artifacts",
        base_name: str = "chart",
    ) -> ArtifactRef | None:
        """Upload a RenderOutput from the chart renderer.

        Args:
            output: RenderOutput from chart_renderer.
            key_prefix: Key prefix for storage.
            base_name: Base filename for key generation.

        Returns:
            ArtifactRef, or None if the output has no content.
        """
        fmt = output.format
        if output.path:
            # File on disk — use upload_file
            return self.upload_file(
                output.path,
                key=f"{key_prefix.rstrip('/')}/{base_name}.{fmt}",
            )

        if output.content is not None:
            ext = fmt
            key = f"{key_prefix.rstrip('/')}/{base_name}.{ext}"
            if isinstance(output.content, bytes):
                return self._upload(
                    output.content,
                    key=key,
                    format=fmt,
                    content_type=_CONTENT_TYPES.get(fmt, "application/octet-stream"),
                )
            elif isinstance(output.content, str):
                return self._upload(
                    output.content.encode("utf-8"),
                    key=key,
                    format=fmt,
                    content_type=_CONTENT_TYPES.get(fmt, "application/octet-stream"),
                )

        log.warning("artifact_store.empty_output", format=fmt)
        return None

    def upload_all_from_pipeline(
        self,
        html_content: str | None = None,
        png_content: bytes | None = None,
        csv_content: str | None = None,
        *,
        key_prefix: str = "artifacts",
        base_name: str = "chart",
    ) -> dict[str, ArtifactRef | None]:
        """Upload all three chart formats at once.

        Returns:
            Dict mapping format → ArtifactRef (or None if that format wasn't provided).
        """
        results: dict[str, ArtifactRef | None] = {}

        if html_content:
            results["html"] = self.upload_html(
                html_content,
                key=f"{key_prefix.rstrip('/')}/{base_name}.html",
            )
        else:
            results["html"] = None

        if png_content:
            results["png"] = self.upload_png(
                png_content,
                key=f"{key_prefix.rstrip('/')}/{base_name}.png",
            )
        else:
            results["png"] = None

        if csv_content:
            results["csv"] = self.upload_csv(
                csv_content,
                key=f"{key_prefix.rstrip('/')}/{base_name}.csv",
            )
        else:
            results["csv"] = None

        return results

    # ── Core upload ──────────────────────────────────────────────────────

    def _upload(
        self,
        data: bytes,
        *,
        key: str,
        format: str,
        content_type: str,
    ) -> ArtifactRef:
        """Internal upload method."""
        size = len(data)
        result = self.client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=size,
            content_type=content_type,
        )
        log.info(
            "artifact_store.uploaded",
            key=key,
            format=format,
            size=size,
            etag=result.etag,
        )
        return ArtifactRef(
            key=key,
            bucket=self._bucket,
            format=format,
            size_bytes=size,
            content_type=content_type,
            created_at=datetime.now(UTC).isoformat(),
            etag=result.etag,
            _store=self,
        )

    # ── URL generation ───────────────────────────────────────────────────

    def presigned_url(
        self,
        key: str,
        *,
        expires_seconds: int = 3600,
        response_headers: dict[str, str] | None = None,
    ) -> str:
        """Generate a presigned GET URL for temporary access.

        Args:
            key: Object key in the bucket.
            expires_seconds: URL lifetime in seconds (default: 1 hour).
            response_headers: Optional response-content-* headers for inline
                display or download (e.g., {'response-content-disposition':
                'inline'}).

        Returns:
            Full presigned URL string, or empty string on error.
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=key,
                expires=timedelta(seconds=expires_seconds),
                response_headers=response_headers,
            )
            log.debug(
                "artifact_store.presigned_url",
                key=key,
                expires_seconds=expires_seconds,
            )
            return url
        except S3Error as exc:
            log.error("artifact_store.presigned_url_failed", key=key, error=str(exc))
            return ""

    def presigned_upload_url(
        self,
        key: str,
        *,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate a presigned PUT URL for direct client uploads.

        Args:
            key: Object key in the bucket.
            expires_seconds: URL lifetime in seconds.

        Returns:
            Full presigned PUT URL, or empty string on error.
        """
        try:
            url = self.client.presigned_put_object(
                bucket_name=self._bucket,
                object_name=key,
                expires=timedelta(seconds=expires_seconds),
            )
            return url
        except S3Error as exc:
            log.error("artifact_store.presigned_upload_url_failed", key=key, error=str(exc))
            return ""

    def public_url(self, key: str) -> str:
        """Generate the public HTTP URL for an object.

        This returns the standard S3 endpoint URL. The object must have
        public-read permissions (bucket policy or object ACL) for this
        URL to be accessible without credentials.

        Args:
            key: Object key in the bucket.

        Returns:
            Public URL string.
        """
        scheme = "https" if self._secure else "http"
        return f"{scheme}://{self._endpoint}/{self._bucket}/{key}"

    # ── Download ─────────────────────────────────────────────────────────

    def download(self, key: str) -> bytes | None:
        """Download an object's content from MinIO.

        Args:
            key: Object key in the bucket.

        Returns:
            Raw bytes, or None if not found or on error.
        """
        try:
            response = self.client.get_object(
                bucket_name=self._bucket,
                object_name=key,
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as exc:
            log.warning("artifact_store.download_failed", key=key, error=str(exc))
            return None

    def download_text(self, key: str) -> str | None:
        """Download an object and decode as UTF-8 text.

        Args:
            key: Object key in the bucket.

        Returns:
            Decoded string, or None if not found.
        """
        data = self.download(key)
        if data is None:
            return None
        return data.decode("utf-8")

    # ── Delete ───────────────────────────────────────────────────────────

    def delete(self, key: str) -> bool:
        """Delete an object from the bucket.

        Args:
            key: Object key to delete.

        Returns:
            True if deleted, False on error.
        """
        try:
            self.client.remove_object(self._bucket, key)
            log.info("artifact_store.deleted", key=key)
            return True
        except S3Error as exc:
            log.warning("artifact_store.delete_failed", key=key, error=str(exc))
            return False

    def delete_many(self, keys: list[str]) -> int:
        """Delete multiple objects. Returns count of successfully deleted."""
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    # ── List ─────────────────────────────────────────────────────────────

    def list_objects(
        self,
        prefix: str = "",
        *,
        recursive: bool = True,
        include_versions: bool = False,
    ) -> list[dict[str, object]]:
        """List objects in the bucket.

        Args:
            prefix: Object key prefix filter.
            recursive: List recursively (vs top-level only).
            include_versions: Include versioned objects.

        Returns:
            List of object info dicts with keys: key, size, etag,
            last_modified, content_type.
        """
        try:
            objects = self.client.list_objects(
                self._bucket,
                prefix=prefix,
                recursive=recursive,
                include_versions=include_versions,
            )
            results: list[dict[str, object]] = []
            for obj in objects:
                results.append(
                    {
                        "key": obj.object_name or "",
                        "size": obj.size or 0,
                        "etag": obj.etag or "",
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else "",
                        "content_type": getattr(obj, "content_type", "") or "",
                    }
                )
            return results
        except S3Error as exc:
            log.warning("artifact_store.list_failed", prefix=prefix, error=str(exc))
            return []

    def list_refs(
        self,
        prefix: str = "",
        *,
        recursive: bool = True,
    ) -> list[ArtifactRef]:
        """List objects as ArtifactRef instances."""
        refs: list[ArtifactRef] = []
        for obj_info in self.list_objects(prefix=prefix, recursive=recursive):
            key = str(obj_info["key"])
            fmt = _ext_to_format(key.rsplit(".", 1)[-1]) if "." in key else "bin"
            refs.append(
                ArtifactRef(
                    key=key,
                    bucket=self._bucket,
                    format=fmt,
                    size_bytes=int(obj_info["size"]),
                    content_type=str(obj_info["content_type"]),
                    created_at=str(obj_info["last_modified"]),
                    etag=str(obj_info["etag"]),
                    _store=self,
                )
            )
        return refs

    # ── Existence check ──────────────────────────────────────────────────

    def exists(self, key: str) -> bool:
        """Check if an object exists in the bucket."""
        try:
            self.client.stat_object(self._bucket, key)
            return True
        except S3Error:
            return False

    def stat(self, key: str) -> dict[str, object] | None:
        """Get object metadata without downloading."""
        try:
            obj = self.client.stat_object(self._bucket, key)
            return {
                "key": obj.object_name or key,
                "size": obj.size or 0,
                "etag": obj.etag or "",
                "content_type": getattr(obj, "content_type", "") or "",
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else "",
            }
        except S3Error:
            return None

    # ── Convenience: bucket info ─────────────────────────────────────────

    @property
    def bucket(self) -> str:
        """Return the configured bucket name."""
        return self._bucket

    @property
    def endpoint(self) -> str:
        """Return the configured endpoint."""
        return self._endpoint
