"""Tests for artifact_store and artifact_vault.

Tests the full MinIO artifact pipeline:
  - ArtifactStore configuration and connection
  - HTML / PNG / CSV / JSON upload
  - Upload from RenderOutput and file paths
  - Presigned URL generation
  - Public URL generation
  - Download and existence check
  - Delete (single and batch)
  - List objects and list_refs
  - Vault archive + restore
  - Cleanup policies (TTL, count, size, dry-run)
  - Edge cases: empty data, missing objects, error paths

All MinIO client calls are mocked — no live MinIO required.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from agents.artifact_store import (
    ArtifactRef,
    ArtifactStore,
    _CONTENT_TYPES,
    _ext_to_format,
    _env,
    _env_bool,
)
from agents.artifact_vault import (
    CleanupPolicy,
    CleanupResult,
    Vault,
    VaultArchive,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_minio_client():
    """Create a fully mocked Minio client."""
    client = MagicMock(name="Minio")
    client.bucket_exists.return_value = True
    return client


@pytest.fixture
def store(mock_minio_client):
    """Create an ArtifactStore with mocked Minio client."""
    with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
        s = ArtifactStore(
            endpoint="localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket="test-bucket",
        )
        s._client = mock_minio_client
        return s


@pytest.fixture
def vault(store):
    """Create a Vault from a mocked store."""
    return Vault(store)


@pytest.fixture
def sample_render_output():
    """Fake RenderOutput for testing upload_from_render_output."""
    ro = MagicMock(name="RenderOutput")
    ro.format = "html"
    ro.path = None
    ro.content = "<html><body>Test</body></html>"
    return ro


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnvHelper:
    def test_env_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("MINIO_BUCKET", raising=False)
        assert _env("MINIO_BUCKET", "aria-artifacts") == "aria-artifacts"

    def test_env_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("MINIO_BUCKET", "my-bucket")
        assert _env("MINIO_BUCKET", "aria-artifacts") == "my-bucket"

    def test_env_bool_true_variants(self, monkeypatch):
        for val in ("1", "true", "True", "TRUE", "yes", "YES"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert _env_bool("TEST_BOOL") is True

    def test_env_bool_false_variants(self, monkeypatch):
        for val in ("0", "false", "False", "FALSE", "no", "NO"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert _env_bool("TEST_BOOL") is False

    def test_env_bool_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert _env_bool("TEST_BOOL", default=True) is True
        assert _env_bool("TEST_BOOL", default=False) is False

    def test_env_bool_default_when_garbage(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "garbage")
        assert _env_bool("TEST_BOOL", default=False) is False


class TestExtToFormat:
    def test_html(self):
        assert _ext_to_format(".html") == "html"
        assert _ext_to_format("html") == "html"
        assert _ext_to_format(".htm") == "html"

    def test_png(self):
        assert _ext_to_format(".png") == "png"

    def test_csv(self):
        assert _ext_to_format(".csv") == "csv"

    def test_json(self):
        assert _ext_to_format(".json") == "json"

    def test_unknown_returns_raw(self):
        assert _ext_to_format(".xyz") == "xyz"

    def test_content_types_coverage(self):
        assert _CONTENT_TYPES["html"] == "text/html; charset=utf-8"
        assert _CONTENT_TYPES["png"] == "image/png"
        assert _CONTENT_TYPES["csv"] == "text/csv; charset=utf-8"
        assert _CONTENT_TYPES["json"] == "application/json; charset=utf-8"


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — configuration
# ═══════════════════════════════════════════════════════════════════════════════


class TestArtifactStoreConfig:
    def test_defaults(self, mock_minio_client):
        with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
            s = ArtifactStore()
            s._client = mock_minio_client
            assert s.bucket == "aria-artifacts"
            assert s.endpoint == "localhost:9000"
            assert s._secure is False

    def test_custom_values(self, mock_minio_client):
        with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
            s = ArtifactStore(
                endpoint="s3.example.com:443",
                bucket="charts",
                secure=True,
                region="eu-west-1",
            )
            s._client = mock_minio_client
            assert s.bucket == "charts"
            assert s.endpoint == "s3.example.com:443"
            assert s._secure is True
            assert s._region == "eu-west-1"

    def test_connect_creates_client(self, mock_minio_client):
        with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
            s = ArtifactStore()
            client = s.connect()
            assert client is mock_minio_client

    def test_connect_creates_bucket_when_missing(self, mock_minio_client):
        mock_minio_client.bucket_exists.return_value = False
        with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
            s = ArtifactStore()
            s._client = mock_minio_client
            s._ensure_bucket()
            mock_minio_client.make_bucket.assert_called_once_with(
                "aria-artifacts", region="us-east-1"
            )

    def test_connect_skips_bucket_when_exists(self, mock_minio_client):
        mock_minio_client.bucket_exists.return_value = True
        with patch("agents.artifact_store.Minio", return_value=mock_minio_client):
            s = ArtifactStore()
            s._client = mock_minio_client
            s._ensure_bucket()
            mock_minio_client.make_bucket.assert_not_called()

    def test_lazy_client_property(self, mock_minio_client):
        s = ArtifactStore()
        # Before connection
        assert s._client is None
        # After setting manually
        s._client = mock_minio_client
        assert s.client is mock_minio_client


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — upload
# ═══════════════════════════════════════════════════════════════════════════════


class TestUpload:
    def test_upload_html(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "abc123"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_html("<h1>Hello</h1>", key="test/chart.html")

        assert ref.key == "test/chart.html"
        assert ref.format == "html"
        assert ref.content_type == "text/html; charset=utf-8"
        assert ref.size_bytes > 0
        assert ref.etag == "abc123"
        assert ref.bucket == "test-bucket"
        mock_minio_client.put_object.assert_called_once()

    def test_upload_html_auto_key(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "abc123"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_html("<div></div>", key_prefix="charts")

        assert ref.key.startswith("charts/")
        assert ref.key.endswith(".html")
        assert ref.format == "html"

    def test_upload_png(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "def456"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_png(b"\x89PNG\r\n\x1a\n", key="test/chart.png")

        assert ref.format == "png"
        assert ref.content_type == "image/png"
        assert ref.size_bytes == 8

    def test_upload_csv(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "ghi789"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_csv("a,b,c\n1,2,3", key="test/data.csv")

        assert ref.format == "csv"
        assert ref.content_type == "text/csv; charset=utf-8"
        assert ref.size_bytes > 0

    def test_upload_json(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "jkl012"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_json('{"count": 42}', key="vault/archive.json")

        assert ref.format == "json"
        assert ref.content_type == "application/json; charset=utf-8"

    def test_upload_file(self, store, mock_minio_client, tmp_path):
        p = tmp_path / "chart.html"
        p.write_text("<html>test</html>", encoding="utf-8")

        put_result = MagicMock()
        put_result.etag = "file123"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_file(p, key="uploads/chart.html")

        assert ref.format == "html"
        assert ref.content_type == "text/html; charset=utf-8"

    def test_upload_file_auto_key_from_filename(self, store, mock_minio_client, tmp_path):
        p = tmp_path / "chart.html"
        p.write_text("<html>test</html>", encoding="utf-8")

        put_result = MagicMock()
        put_result.etag = "auto123"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_file(p, key_prefix="auto")

        assert ref.key == f"auto/{p.name}"

    def test_upload_file_unknown_extension(self, store, mock_minio_client, tmp_path):
        p = tmp_path / "data.bin"
        p.write_bytes(b"\x00\x01\x02")

        put_result = MagicMock()
        put_result.etag = "bin123"
        mock_minio_client.put_object.return_value = put_result

        ref = store.upload_file(p)

        assert ref.format == "bin"
        assert ref.content_type == "application/octet-stream"

    def test_upload_from_render_output_in_memory(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "ro123"
        mock_minio_client.put_object.return_value = put_result

        ro = MagicMock()
        ro.format = "html"
        ro.path = None
        ro.content = "<html><body>Chart</body></html>"

        ref = store.upload_from_render_output(ro, base_name="my_chart")

        assert ref is not None
        assert ref.key == "artifacts/my_chart.html"
        assert ref.format == "html"

    def test_upload_from_render_output_file_on_disk(self, store, mock_minio_client, tmp_path):
        p = tmp_path / "chart.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")

        put_result = MagicMock()
        put_result.etag = "disk123"
        mock_minio_client.put_object.return_value = put_result

        ro = MagicMock()
        ro.format = "png"
        ro.path = str(p)
        ro.content = None

        ref = store.upload_from_render_output(ro, base_name="my_chart")

        assert ref is not None
        assert ref.key == "artifacts/my_chart.png"

    def test_upload_from_render_output_empty(self, store):
        ro = MagicMock()
        ro.format = "html"
        ro.path = None
        ro.content = None

        ref = store.upload_from_render_output(ro)
        assert ref is None

    def test_upload_from_render_output_bytes_content(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "bytes123"
        mock_minio_client.put_object.return_value = put_result

        ro = MagicMock()
        ro.format = "png"
        ro.path = None
        ro.content = b"\x89PNG\r\n\x1a\n"

        ref = store.upload_from_render_output(ro)
        assert ref is not None
        assert ref.format == "png"

    def test_upload_all_from_pipeline(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "multi123"
        mock_minio_client.put_object.return_value = put_result

        results = store.upload_all_from_pipeline(
            html_content="<html>test</html>",
            png_content=b"\x89PNG\r\n\x1a\n",
            csv_content="a,b\n1,2",
            key_prefix="conv/42",
            base_name="chart_001",
        )

        assert results["html"] is not None
        assert results["html"].key == "conv/42/chart_001.html"
        assert results["png"] is not None
        assert results["png"].key == "conv/42/chart_001.png"
        assert results["csv"] is not None
        assert results["csv"].key == "conv/42/chart_001.csv"

    def test_upload_all_from_pipeline_partial(self, store, mock_minio_client):
        put_result = MagicMock()
        put_result.etag = "part123"
        mock_minio_client.put_object.return_value = put_result

        results = store.upload_all_from_pipeline(
            html_content="<html>test</html>",
        )

        assert results["html"] is not None
        assert results["png"] is None
        assert results["csv"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — URLs
# ═══════════════════════════════════════════════════════════════════════════════


class TestUrls:
    def test_presigned_url(self, store, mock_minio_client):
        mock_minio_client.presigned_get_object.return_value = (
            "http://localhost:9000/test-bucket/test/chart.html?X-Amz-..."
        )

        url = store.presigned_url("test/chart.html", expires_seconds=3600)

        assert "localhost:9000" in url
        mock_minio_client.presigned_get_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="test/chart.html",
            expires=mock.ANY,
            response_headers=None,
        )

    def test_presigned_url_with_response_headers(self, store, mock_minio_client):
        mock_minio_client.presigned_get_object.return_value = "http://..."

        url = store.presigned_url(
            "test/chart.html",
            response_headers={"response-content-disposition": "inline"},
        )

        assert "http://" in url
        mock_minio_client.presigned_get_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="test/chart.html",
            expires=mock.ANY,
            response_headers={"response-content-disposition": "inline"},
        )

    def test_presigned_url_error_returns_empty(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.presigned_get_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/missing.html",
            request_id="req123", host_id="host456",
            response=None,
        )

        url = store.presigned_url("missing.html")
        assert url == ""

    def test_presigned_upload_url(self, store, mock_minio_client):
        mock_minio_client.presigned_put_object.return_value = "http://...put..."

        url = store.presigned_upload_url("uploads/new.png")
        assert "http://" in url

    def test_public_url_http(self, store):
        store._secure = False
        url = store.public_url("test/chart.html")
        assert url == "http://localhost:9000/test-bucket/test/chart.html"

    def test_public_url_https(self, store):
        store._secure = True
        url = store.public_url("test/chart.html")
        assert url == "https://localhost:9000/test-bucket/test/chart.html"

    def test_artifact_ref_presigned_url(self, store, mock_minio_client):
        mock_minio_client.presigned_get_object.return_value = "http://presigned/..."

        ref = ArtifactRef(
            key="test/chart.html",
            bucket="test-bucket",
            format="html",
            size_bytes=100,
            content_type="text/html",
            created_at="2026-01-01T00:00:00Z",
            _store=store,
        )

        url = ref.presigned_url(expires=1800)
        assert "http://" in url

    def test_artifact_ref_public_url(self, store):
        store._secure = False
        ref = ArtifactRef(
            key="test/chart.html",
            bucket="test-bucket",
            format="html",
            size_bytes=100,
            content_type="text/html",
            created_at="2026-01-01T00:00:00Z",
            _store=store,
        )

        assert ref.public_url() == "http://localhost:9000/test-bucket/test/chart.html"

    def test_artifact_ref_without_store_returns_empty(self):
        ref = ArtifactRef(
            key="test/chart.html",
            bucket="test-bucket",
            format="html",
            size_bytes=100,
            content_type="text/html",
            created_at="2026-01-01T00:00:00Z",
            _store=None,
        )

        assert ref.presigned_url() == ""
        assert ref.public_url() == ""
        assert ref.delete() is False


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — download
# ═══════════════════════════════════════════════════════════════════════════════


class TestDownload:
    def test_download_bytes(self, store, mock_minio_client):
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>test</html>"
        mock_minio_client.get_object.return_value = mock_response

        data = store.download("test/chart.html")
        assert data == b"<html>test</html>"

    def test_download_text(self, store, mock_minio_client):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"a":1}'
        mock_minio_client.get_object.return_value = mock_response

        text = store.download_text("vault/archive.json")
        assert text == '{"a":1}'

    def test_download_not_found(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/missing.html",
            request_id="req123", host_id="host456",
            response=None,
        )

        assert store.download("missing.html") is None
        assert store.download_text("missing.html") is None


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — delete
# ═══════════════════════════════════════════════════════════════════════════════


class TestDelete:
    def test_delete_success(self, store, mock_minio_client):
        assert store.delete("test/chart.html") is True
        mock_minio_client.remove_object.assert_called_once_with(
            "test-bucket", "test/chart.html"
        )

    def test_delete_failure(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.remove_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/missing.html",
            request_id="req123", host_id="host456",
            response=None,
        )

        assert store.delete("missing.html") is False

    def test_delete_many(self, store, mock_minio_client):
        assert store.delete_many(["a.html", "b.png", "c.csv"]) == 3

    def test_delete_many_partial(self, store, mock_minio_client):
        from minio.error import S3Error

        call_count = 0
        original = mock_minio_client.remove_object

        def side_effect(bucket, key):
            nonlocal call_count
            call_count += 1
            if key == "b.png":
                raise S3Error(
                    code="NoSuchKey", message="Not found",
                    resource="/test-bucket/b.png",
                    request_id="req123", host_id="host456",
                    response=None,
                )

        mock_minio_client.remove_object.side_effect = side_effect

        assert store.delete_many(["a.html", "b.png", "c.csv"]) == 2

    def test_artifact_ref_delete(self, store, mock_minio_client):
        ref = ArtifactRef(
            key="test/chart.html",
            bucket="test-bucket",
            format="html",
            size_bytes=100,
            content_type="text/html",
            created_at="2026-01-01T00:00:00Z",
            _store=store,
        )

        assert ref.delete() is True
        mock_minio_client.remove_object.assert_called_once_with(
            "test-bucket", "test/chart.html"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ArtifactStore — list / exists / stat
# ═══════════════════════════════════════════════════════════════════════════════


class TestListAndCheck:
    def test_list_objects(self, store, mock_minio_client):
        obj1 = MagicMock()
        obj1.object_name = "artifacts/chart.html"
        obj1.size = 500
        obj1.etag = "abc"
        obj1.last_modified = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)
        obj1.content_type = "text/html"

        obj2 = MagicMock()
        obj2.object_name = "artifacts/chart.png"
        obj2.size = 2000
        obj2.etag = "def"
        obj2.last_modified = datetime(2026, 6, 7, 12, 1, 0, tzinfo=timezone.utc)
        obj2.content_type = "image/png"

        mock_minio_client.list_objects.return_value = [obj1, obj2]

        results = store.list_objects(prefix="artifacts/")

        assert len(results) == 2
        assert results[0]["key"] == "artifacts/chart.html"
        assert results[0]["size"] == 500
        assert results[1]["key"] == "artifacts/chart.png"

    def test_list_objects_error_returns_empty(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.list_objects.side_effect = S3Error(
            code="AccessDenied", message="Denied",
            resource="/test-bucket", request_id="req", host_id="host",
            response=None,
        )

        assert store.list_objects(prefix="secret/") == []

    def test_list_refs(self, store, mock_minio_client):
        obj1 = MagicMock()
        obj1.object_name = "charts/a.html"
        obj1.size = 100
        obj1.etag = "etag1"
        obj1.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj1.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj1]

        refs = store.list_refs(prefix="charts/")

        assert len(refs) == 1
        assert refs[0].key == "charts/a.html"
        assert refs[0].format == "html"
        assert isinstance(refs[0], ArtifactRef)

    def test_exists_true(self, store, mock_minio_client):
        mock_minio_client.stat_object.return_value = MagicMock()
        assert store.exists("test/chart.html") is True

    def test_exists_false(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/missing.html",
            request_id="req", host_id="host",
            response=None,
        )
        assert store.exists("missing.html") is False

    def test_stat(self, store, mock_minio_client):
        stat = MagicMock()
        stat.object_name = "test/chart.html"
        stat.size = 1234
        stat.etag = "etag_stat"
        stat.content_type = "text/html"
        stat.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)

        mock_minio_client.stat_object.return_value = stat

        info = store.stat("test/chart.html")
        assert info is not None
        assert info["key"] == "test/chart.html"
        assert info["size"] == 1234

    def test_stat_not_found(self, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/missing.html",
            request_id="req", host_id="host",
            response=None,
        )
        assert store.stat("missing.html") is None


# ═══════════════════════════════════════════════════════════════════════════════
# Vault — archive
# ═══════════════════════════════════════════════════════════════════════════════


class TestVaultArchive:
    def test_archive_creates_json(self, vault, store, mock_minio_client):
        # Set up list_objects to return some artifacts
        obj = MagicMock()
        obj.object_name = "artifacts/chart.html"
        obj.size = 500
        obj.etag = "etag1"
        obj.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        put_result = MagicMock()
        put_result.etag = "vault123"
        mock_minio_client.put_object.return_value = put_result

        ref = vault.archive(prefix="artifacts/")

        assert ref is not None
        assert ref.format == "json"
        assert ref.key.startswith("vault/archive_")
        mock_minio_client.put_object.assert_called_once()

    def test_archive_empty_prefix(self, vault, mock_minio_client):
        mock_minio_client.list_objects.return_value = []

        ref = vault.archive(prefix="empty/")
        assert ref is None

    def test_archive_excludes_vault_prefix(self, vault, mock_minio_client):
        # One artifact under artifacts/, one under vault/
        obj_artifact = MagicMock()
        obj_artifact.object_name = "artifacts/chart.html"
        obj_artifact.size = 100
        obj_artifact.etag = "etag_art"
        obj_artifact.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj_artifact.content_type = "text/html"

        obj_vault = MagicMock()
        obj_vault.object_name = "vault/old_archive.json"
        obj_vault.size = 200
        obj_vault.etag = "etag_vault"
        obj_vault.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj_vault.content_type = "application/json"

        mock_minio_client.list_objects.return_value = [obj_artifact, obj_vault]

        put_result = MagicMock()
        put_result.etag = "clean_vault"
        mock_minio_client.put_object.return_value = put_result

        ref = vault.archive(prefix="")

        # Should only include artifact, not vault file
        assert ref is not None
        # Verify the uploaded JSON only has 1 artifact (not 2)
        call_args = mock_minio_client.put_object.call_args
        data = call_args[1]["data"].getvalue()
        archive_dict = json.loads(data)
        assert archive_dict["artifact_count"] == 1

    def test_archive_custom_name(self, vault, mock_minio_client):
        obj = MagicMock()
        obj.object_name = "artifacts/chart.html"
        obj.size = 100
        obj.etag = "etag"
        obj.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        put_result = MagicMock()
        put_result.etag = "custom123"
        mock_minio_client.put_object.return_value = put_result

        ref = vault.archive(prefix="artifacts/", archive_name="my_archive.json")
        assert ref is not None
        assert ref.key == "vault/my_archive.json"


# ═══════════════════════════════════════════════════════════════════════════════
# Vault — restore
# ═══════════════════════════════════════════════════════════════════════════════


class TestVaultRestore:
    def test_restore_valid_archive(self, vault, store, mock_minio_client):
        archive_json = json.dumps({
            "archive_id": "abc123",
            "created_at": "2026-06-07T12:00:00Z",
            "prefix": "artifacts/",
            "artifact_count": 2,
            "total_size_bytes": 1500,
            "artifacts": [
                {"key": "artifacts/a.html", "size": 500, "etag": "e1"},
                {"key": "artifacts/b.png", "size": 1000, "etag": "e2"},
            ],
        })

        mock_response = MagicMock()
        mock_response.read.return_value = archive_json.encode("utf-8")
        mock_minio_client.get_object.return_value = mock_response

        manifest = vault.restore("vault/archive_2026-06-07.json")

        assert manifest is not None
        assert manifest.archive_id == "abc123"
        assert manifest.artifact_count == 2
        assert manifest.total_size_bytes == 1500
        assert len(manifest.artifacts) == 2
        assert manifest.artifacts[0]["key"] == "artifacts/a.html"

    def test_restore_not_found(self, vault, store, mock_minio_client):
        from minio.error import S3Error

        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchKey", message="Not found",
            resource="/test-bucket/vault/missing.json",
            request_id="req", host_id="host",
            response=None,
        )

        manifest = vault.restore("vault/missing.json")
        assert manifest is None

    def test_restore_invalid_json(self, vault, store, mock_minio_client):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json {{"
        mock_minio_client.get_object.return_value = mock_response

        manifest = vault.restore("vault/bad.json")
        assert manifest is None

    def test_list_archives(self, vault, mock_minio_client):
        obj1 = MagicMock()
        obj1.object_name = "vault/archive_1.json"
        obj1.size = 100
        obj1.etag = "e1"
        obj1.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj1.content_type = "application/json"

        obj2 = MagicMock()
        obj2.object_name = "vault/not_archive.txt"
        obj2.size = 50
        obj2.etag = "e2"
        obj2.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj2.content_type = "text/plain"

        mock_minio_client.list_objects.return_value = [obj1, obj2]

        archives = vault.list_archives()
        assert len(archives) == 1
        assert archives[0]["key"] == "vault/archive_1.json"


# ═══════════════════════════════════════════════════════════════════════════════
# CleanupPolicy
# ═══════════════════════════════════════════════════════════════════════════════


class TestCleanupPolicy:
    def test_standard_policy(self):
        p = CleanupPolicy.standard()
        assert p.max_age_days == 30
        assert p.max_count is None
        assert p.max_size_bytes is None

    def test_aggressive_policy(self):
        p = CleanupPolicy.aggressive()
        assert p.max_age_days == 7
        assert p.max_count == 1000
        assert p.max_size_bytes is None

    def test_size_based_policy(self):
        p = CleanupPolicy.size_based(max_size_mb=500)
        assert p.max_age_days is None
        assert p.max_count is None
        assert p.max_size_bytes == 524288000  # 500 * 1024 * 1024

    def test_invalid_max_age_raises(self):
        with pytest.raises(ValueError):
            CleanupPolicy(max_age_days=-1)

    def test_invalid_max_count_raises(self):
        with pytest.raises(ValueError):
            CleanupPolicy(max_count=-5)

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            CleanupPolicy(max_size_bytes=-100)

    def test_exclude_formats_default(self):
        p = CleanupPolicy()
        assert "json" in p.exclude_formats

    def test_exclude_formats_custom(self):
        p = CleanupPolicy(exclude_formats=["json", "html"])
        assert p.exclude_formats == ["json", "html"]


# ═══════════════════════════════════════════════════════════════════════════════
# Vault — cleanup
# ═══════════════════════════════════════════════════════════════════════════════


class TestVaultCleanup:
    def test_cleanup_dry_run(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

        obj = MagicMock()
        obj.object_name = "artifacts/old_chart.html"
        obj.size = 500
        obj.etag = "e1"
        obj.last_modified = old_date
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy(max_age_days=30),
            dry_run=True,
        )

        assert result.dry_run is True
        assert len(result.candidates) == 1
        assert len(result.deleted) == 0
        assert result.bytes_freed == 0
        assert mock_minio_client.remove_object.call_count == 0

    def test_cleanup_execute(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

        obj = MagicMock()
        obj.object_name = "artifacts/old_chart.html"
        obj.size = 500
        obj.etag = "e1"
        obj.last_modified = old_date
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy(max_age_days=30),
            dry_run=False,
        )

        assert result.dry_run is False
        assert len(result.deleted) == 1
        assert result.bytes_freed == 500
        mock_minio_client.remove_object.assert_called_once()

    def test_cleanup_excludes_vault_json(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

        obj1 = MagicMock()
        obj1.object_name = "artifacts/chart.html"
        obj1.size = 500
        obj1.etag = "e1"
        obj1.last_modified = old_date
        obj1.content_type = "text/html"

        obj2 = MagicMock()
        obj2.object_name = "vault/archive.json"
        obj2.size = 1000
        obj2.etag = "e2"
        obj2.last_modified = old_date
        obj2.content_type = "application/json"

        mock_minio_client.list_objects.return_value = [obj1, obj2]

        result = vault.cleanup(
            prefix="",
            policy=CleanupPolicy(max_age_days=30),
            dry_run=True,
        )

        # Only chart.html should be a candidate; vault/archive.json excluded
        assert len(result.candidates) == 1
        assert result.candidates[0] == "artifacts/chart.html"

    def test_cleanup_not_old_enough(self, vault, mock_minio_client):
        recent_date = datetime.now(timezone.utc) - timedelta(days=5)

        obj = MagicMock()
        obj.object_name = "artifacts/recent.html"
        obj.size = 500
        obj.etag = "e1"
        obj.last_modified = recent_date
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy(max_age_days=30),
            dry_run=True,
        )

        assert len(result.candidates) == 0

    def test_cleanup_max_count(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mid_date = datetime(2026, 3, 1, tzinfo=timezone.utc)

        obj1 = MagicMock()
        obj1.object_name = "artifacts/oldest.html"
        obj1.size = 100
        obj1.etag = "e1"
        obj1.last_modified = old_date
        obj1.content_type = "text/html"

        obj2 = MagicMock()
        obj2.object_name = "artifacts/newer.html"
        obj2.size = 200
        obj2.etag = "e2"
        obj2.last_modified = mid_date
        obj2.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj1, obj2]

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy(max_count=1),
            dry_run=True,
        )

        # Should keep only 1 — the newest
        assert len(result.candidates) == 1
        # Oldest should be candidate for deletion
        assert result.candidates[0] == "artifacts/oldest.html"

    def test_cleanup_max_size(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

        obj = MagicMock()
        obj.object_name = "artifacts/large.html"
        obj.size = 10_000_000  # 10 MB
        obj.etag = "e1"
        obj.last_modified = old_date
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy.size_based(max_size_mb=5),  # 5 MB limit
            dry_run=True,
        )

        assert len(result.candidates) == 1

    def test_cleanup_combined_policy(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

        objs = []
        for i in range(5):
            o = MagicMock()
            o.object_name = f"artifacts/chart_{i}.html"
            o.size = 1000
            o.etag = f"e{i}"
            o.last_modified = old_date + timedelta(days=i)
            o.content_type = "text/html"
            objs.append(o)

        mock_minio_client.list_objects.return_value = objs

        result = vault.cleanup(
            prefix="artifacts/",
            policy=CleanupPolicy(max_age_days=30, max_count=2),
            dry_run=True,
        )

        # All are old, but max_count=2 — keep 2 newest
        assert len(result.candidates) == 3

    def test_purge_old_convenience(self, vault, mock_minio_client):
        old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        obj = MagicMock()
        obj.object_name = "artifacts/old.html"
        obj.size = 500
        obj.etag = "e1"
        obj.last_modified = old_date
        obj.content_type = "text/html"

        mock_minio_client.list_objects.return_value = [obj]

        result = vault.purge_old(prefix="artifacts/", max_age_days=30, dry_run=True)
        assert len(result.candidates) == 1

    def test_purge_excess_convenience(self, vault, mock_minio_client):
        objs = []
        for i in range(5):
            o = MagicMock()
            o.object_name = f"artifacts/chart_{i}.html"
            o.size = 100
            o.etag = f"e{i}"
            o.last_modified = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
            o.content_type = "text/html"
            objs.append(o)

        mock_minio_client.list_objects.return_value = objs

        result = vault.purge_excess(prefix="artifacts/", max_count=2, dry_run=True)
        assert len(result.candidates) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Vault — stats
# ═══════════════════════════════════════════════════════════════════════════════


class TestVaultStats:
    def test_stats(self, vault, mock_minio_client):
        obj1 = MagicMock()
        obj1.object_name = "artifacts/a.html"
        obj1.size = 500
        obj1.etag = "e1"
        obj1.last_modified = datetime(2026, 1, 1, tzinfo=timezone.utc)
        obj1.content_type = "text/html"

        obj2 = MagicMock()
        obj2.object_name = "artifacts/b.png"
        obj2.size = 1500
        obj2.etag = "e2"
        obj2.last_modified = datetime(2026, 6, 7, tzinfo=timezone.utc)
        obj2.content_type = "image/png"

        mock_minio_client.list_objects.return_value = [obj1, obj2]

        stats = vault.stats(prefix="artifacts/")

        assert stats["count"] == 2
        assert stats["total_size_bytes"] == 2000
        assert stats["by_format"]["html"]["count"] == 1
        assert stats["by_format"]["html"]["total_size_bytes"] == 500
        assert stats["by_format"]["png"]["count"] == 1
        assert stats["by_format"]["png"]["total_size_bytes"] == 1500

    def test_stats_empty(self, vault, mock_minio_client):
        mock_minio_client.list_objects.return_value = []

        stats = vault.stats(prefix="empty/")
        assert stats["count"] == 0
        assert stats["total_size_bytes"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Integration — import sanity
# ═══════════════════════════════════════════════════════════════════════════════


class TestImports:
    def test_agents_init_exports_all(self):
        """Verify agents package exports all expected names."""
        from agents import (
            ArtifactRef,
            ArtifactStore,
            CleanupPolicy,
            CleanupResult,
            Vault,
            VaultArchive,
            ChartConfig,
            ChartType,
            render_html,
            run_chart_pipeline_sync,
        )
        # If we got here without ImportError, exports work
        assert ArtifactStore is not None
        assert Vault is not None

    def test_artifact_store_can_import_render_types(self):
        """ArtifactStore imports chart_renderer types lazily (TYPE_CHECKING)."""
        import agents.artifact_store  # noqa: F401 — just loading the module
        # Module should import without error even if chart_renderer
        # is not fully available.
