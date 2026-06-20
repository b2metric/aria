"""Artifact Vault — JSON archive, restore, and cleanup/purge policy.

The vault provides:

1. **Archive** — Periodically serialize all artifact metadata to a JSON
   snapshot stored in MinIO (vault/ prefix). This enables disaster recovery
   and offline analysis of artifact history.

2. **Restore** — Load a vault snapshot and optionally re-download artifacts.

3. **Cleanup / Purge** — Policy-driven removal of old artifacts:
   - **TTL** (time-to-live): delete artifacts older than N days
   - **Max Count**: delete oldest when count exceeds limit (per prefix)
   - **Max Size**: delete oldest when total bytes exceed limit (per prefix)
   - **Dry Run**: preview what would be deleted without acting

Usage:
    from agents.artifact_store import ArtifactStore
    from agents.artifact_vault import Vault, CleanupPolicy

    store = ArtifactStore()
    vault = Vault(store)

    # Archive all artifacts
    ref = vault.archive(prefix="artifacts/")

    # Restore from vault
    manifest = vault.restore("vault/archive_2026-06-07.json")

    # Cleanup: delete artifacts older than 30 days
    policy = CleanupPolicy(max_age_days=30)
    deleted = vault.cleanup(prefix="artifacts/", policy=policy, dry_run=False)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from agents.artifact_store import ArtifactRef, ArtifactStore

log = structlog.get_logger(__name__)


# ── Cleanup policy ──────────────────────────────────────────────────────────


@dataclass
class CleanupPolicy:
    """Rules for artifact cleanup/purge.

    All conditions are ANDed — an artifact is eligible for deletion if it
    matches ALL enabled rules. Set a rule to None to disable it.
    """

    max_age_days: int | None = None
    """Delete artifacts older than this many days (from created_at)."""

    max_count: int | None = None
    """If set, keep at most this many artifacts in the prefix (delete oldest)."""

    max_size_bytes: int | None = None
    """If set, keep total size under this limit (delete oldest first)."""

    exclude_formats: list[str] = field(default_factory=lambda: ["json"])
    """Never delete artifacts with these formats (default: json = vault files)."""

    def __post_init__(self) -> None:
        if self.max_age_days is not None and self.max_age_days < 0:
            raise ValueError("max_age_days must be >= 0")
        if self.max_count is not None and self.max_count < 0:
            raise ValueError("max_count must be >= 0")
        if self.max_size_bytes is not None and self.max_size_bytes < 0:
            raise ValueError("max_size_bytes must be >= 0")

    @classmethod
    def standard(cls) -> CleanupPolicy:
        """Standard policy: 30-day TTL, no count/size limits."""
        return cls(max_age_days=30)

    @classmethod
    def aggressive(cls) -> CleanupPolicy:
        """Aggressive policy: 7-day TTL, max 1000 artifacts."""
        return cls(max_age_days=7, max_count=1000)

    @classmethod
    def size_based(cls, max_size_mb: int = 500) -> CleanupPolicy:
        """Size-based policy: delete oldest when total exceeds max_size_mb megabytes."""
        return cls(max_size_bytes=max_size_mb * 1024 * 1024)


# ── Cleanup result ──────────────────────────────────────────────────────────


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    policy: CleanupPolicy
    """The policy that was applied."""

    prefix: str
    """Prefix that was cleaned."""

    candidates: list[str]
    """Keys that matched the policy (would be deleted)."""

    deleted: list[str]
    """Keys that were actually deleted (empty on dry_run)."""

    bytes_freed: int = 0
    """Total bytes freed (0 on dry_run)."""

    dry_run: bool = False
    """Whether this was a dry run."""


# ── Vault ───────────────────────────────────────────────────────────────────


@dataclass
class VaultArchive:
    """A vault snapshot containing artifact metadata."""

    archive_id: str
    """Unique archive identifier."""

    created_at: str
    """ISO 8601 timestamp of archive creation."""

    prefix: str
    """Prefix that was archived."""

    artifact_count: int
    """Number of artifacts in the archive."""

    total_size_bytes: int
    """Total size of all artifacts."""

    artifacts: list[dict[str, object]]
    """List of artifact metadata dicts (key, size, format, content_type, etag, last_modified)."""

    archive_ref: ArtifactRef | None = None
    """Reference to the archive JSON in MinIO (set after upload)."""


class Vault:
    """Archive and restore artifacts with cleanup policies.

    Wraps an ``ArtifactStore`` to provide archival, restore, and
    policy-driven cleanup of stored chart artifacts.
    """

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    # ── Archive ──────────────────────────────────────────────────────────

    def archive(
        self,
        prefix: str = "",
        *,
        archive_name: str | None = None,
        vault_prefix: str = "vault",
    ) -> ArtifactRef | None:
        """Create a JSON archive of all artifacts under a prefix.

        The archive is uploaded to MinIO as a JSON file in the vault prefix.

        Args:
            prefix: Object key prefix to archive.
            archive_name: Custom archive filename (auto-generated if None).
            vault_prefix: Prefix for the archive JSON file.

        Returns:
            ArtifactRef for the archive JSON, or None if no artifacts found.
        """
        artifacts = self._store.list_objects(prefix=prefix, recursive=True)

        # Filter out vault files themselves to avoid archive recursion
        artifacts = [a for a in artifacts if not str(a["key"]).startswith(vault_prefix)]

        if not artifacts:
            log.warning("vault.archive_empty", prefix=prefix)
            return None

        total_size = sum(int(a.get("size", 0)) for a in artifacts)

        if archive_name is None:
            ts = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
            archive_name = f"archive_{ts}.json"

        archive_data: dict[str, object] = {
            "archive_id": uuid.uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "prefix": prefix,
            "artifact_count": len(artifacts),
            "total_size_bytes": total_size,
            "artifacts": artifacts,
        }

        json_str = json.dumps(archive_data, indent=2, ensure_ascii=False, default=str)
        key = f"{vault_prefix.rstrip('/')}/{archive_name}"

        ref = self._store.upload_json(json_str, key=key, key_prefix=vault_prefix)
        log.info(
            "vault.archived",
            archive_id=archive_data["archive_id"],
            key=key,
            count=len(artifacts),
            total_size=total_size,
        )
        return ref

    # ── Restore ──────────────────────────────────────────────────────────

    def restore(self, key: str) -> VaultArchive | None:
        """Restore a vault archive from MinIO by key.

        Args:
            key: Object key of the vault JSON file (e.g. 'vault/archive_2026-06-07.json').

        Returns:
            VaultArchive with full metadata, or None if not found.
        """
        data = self._store.download_text(key)
        if data is None:
            log.warning("vault.restore_not_found", key=key)
            return None

        try:
            archive_dict = json.loads(data)
        except json.JSONDecodeError as exc:
            log.error("vault.restore_json_error", key=key, error=str(exc))
            return None

        artifacts_raw = archive_dict.get("artifacts", [])
        if isinstance(artifacts_raw, list):
            artifacts: list[dict[str, object]] = [
                dict(a) if isinstance(a, dict) else {"key": str(a)} for a in artifacts_raw
            ]
        else:
            artifacts = []

        archive = VaultArchive(
            archive_id=str(archive_dict.get("archive_id", "")),
            created_at=str(archive_dict.get("created_at", "")),
            prefix=str(archive_dict.get("prefix", "")),
            artifact_count=int(archive_dict.get("artifact_count", 0)),
            total_size_bytes=int(archive_dict.get("total_size_bytes", 0)),
            artifacts=artifacts,
        )

        log.info(
            "vault.restored",
            archive_id=archive.archive_id,
            key=key,
            count=len(artifacts),
        )
        return archive

    def list_archives(self, vault_prefix: str = "vault") -> list[dict[str, object]]:
        """List all vault archive files.

        Returns:
            List of object info dicts for .json files under vault_prefix.
        """
        all_objects = self._store.list_objects(prefix=vault_prefix, recursive=True)
        return [o for o in all_objects if str(o["key"]).endswith(".json")]

    # ── Cleanup ──────────────────────────────────────────────────────────

    def cleanup(
        self,
        prefix: str = "",
        *,
        policy: CleanupPolicy | None = None,
        dry_run: bool = True,
    ) -> CleanupResult:
        """Apply cleanup policy to artifacts under a prefix.

        Args:
            prefix: Object key prefix to clean.
            policy: Cleanup rules (default: standard 30-day TTL).
            dry_run: If True, only identify candidates without deleting.

        Returns:
            CleanupResult with candidates and (if not dry_run) deleted keys.
        """
        if policy is None:
            policy = CleanupPolicy.standard()

        artifacts = self._store.list_objects(prefix=prefix, recursive=True)
        candidates: list[dict[str, object]] = []

        now = datetime.now(UTC)

        # ── Stage 1: Identify candidates by policy ────────────────────
        for art in artifacts:
            key = str(art["key"])

            # Exclude by format
            ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
            if ext in policy.exclude_formats:
                continue

            eligible = True

            # TTL check
            if policy.max_age_days is not None:
                lm_str = str(art.get("last_modified", ""))
                if lm_str:
                    try:
                        lm = datetime.fromisoformat(lm_str)
                        age_days = (now - lm).total_seconds() / 86400
                        if age_days <= policy.max_age_days:
                            eligible = False
                    except (ValueError, TypeError):
                        pass  # Can't parse date — keep it (conservative)

            if eligible:
                candidates.append(art)

        # ── Stage 2: Count-based pruning ──────────────────────────────
        if policy.max_count is not None and len(candidates) > policy.max_count:
            # Sort by last_modified ascending (oldest first)
            candidates.sort(
                key=lambda a: str(a.get("last_modified", "")),
            )
            # Keep the NEWEST max_count items; delete the rest (oldest)
            keep_count = policy.max_count
            candidates = candidates[: len(candidates) - keep_count]

        # ── Stage 3: Size-based pruning ───────────────────────────────
        if policy.max_size_bytes is not None:
            # Sort by last_modified ascending (oldest first)
            candidates.sort(
                key=lambda a: str(a.get("last_modified", "")),
            )
            # Walk from newest to oldest, keeping items that still fit
            kept: list[dict[str, object]] = []
            kept_total = 0
            for art in reversed(candidates):
                sz = int(art.get("size", 0))
                if kept_total + sz <= policy.max_size_bytes:
                    kept.append(art)
                    kept_total += sz
            kept_keys = {str(a["key"]) for a in kept}
            candidates = [a for a in candidates if str(a["key"]) not in kept_keys]

        # ── Execute ───────────────────────────────────────────────────
        candidate_keys = [str(a["key"]) for a in candidates]

        if dry_run:
            return CleanupResult(
                policy=policy,
                prefix=prefix,
                candidates=candidate_keys,
                deleted=[],
                bytes_freed=0,
                dry_run=True,
            )

        deleted_keys: list[str] = []
        bytes_freed = 0
        for art in candidates:
            key = str(art["key"])
            if self._store.delete(key):
                deleted_keys.append(key)
                bytes_freed += int(art.get("size", 0))

        log.info(
            "vault.cleanup_complete",
            prefix=prefix,
            candidates=len(candidate_keys),
            deleted=len(deleted_keys),
            bytes_freed=bytes_freed,
        )

        return CleanupResult(
            policy=policy,
            prefix=prefix,
            candidates=candidate_keys,
            deleted=deleted_keys,
            bytes_freed=bytes_freed,
            dry_run=False,
        )

    # ── Purge convenience ────────────────────────────────────────────────

    def purge_old(
        self,
        prefix: str = "",
        *,
        max_age_days: int = 30,
        dry_run: bool = True,
    ) -> CleanupResult:
        """Delete artifacts older than max_age_days.

        Convenience wrapper around cleanup().
        """
        return self.cleanup(
            prefix=prefix,
            policy=CleanupPolicy(max_age_days=max_age_days),
            dry_run=dry_run,
        )

    def purge_excess(
        self,
        prefix: str = "",
        *,
        max_count: int = 1000,
        dry_run: bool = True,
    ) -> CleanupResult:
        """Delete oldest artifacts when count exceeds max_count."""
        return self.cleanup(
            prefix=prefix,
            policy=CleanupPolicy(max_count=max_count),
            dry_run=dry_run,
        )

    def purge_by_size(
        self,
        prefix: str = "",
        *,
        max_size_mb: int = 500,
        dry_run: bool = True,
    ) -> CleanupResult:
        """Delete oldest artifacts when total size exceeds max_size_mb."""
        return self.cleanup(
            prefix=prefix,
            policy=CleanupPolicy.size_based(max_size_mb=max_size_mb),
            dry_run=dry_run,
        )

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self, prefix: str = "") -> dict[str, object]:
        """Return aggregate statistics for artifacts under a prefix.

        Returns:
            Dict with count, total_size_bytes, oldest, newest,
            by_format (counts and sizes per format).
        """
        artifacts = self._store.list_objects(prefix=prefix, recursive=True)

        if not artifacts:
            return {
                "count": 0,
                "total_size_bytes": 0,
                "by_format": {},
            }

        total_size = 0
        by_format: dict[str, dict[str, int]] = {}
        oldest: str | None = None
        newest: str | None = None

        for art in artifacts:
            size = int(art.get("size", 0))
            total_size += size

            key = str(art["key"])
            ext = key.rsplit(".", 1)[-1].lower() if "." in key else "bin"
            if ext not in by_format:
                by_format[ext] = {"count": 0, "total_size_bytes": 0}
            by_format[ext]["count"] += 1
            by_format[ext]["total_size_bytes"] += size

            lm = str(art.get("last_modified", ""))
            if lm:
                if oldest is None or lm < oldest:
                    oldest = lm
                if newest is None or lm > newest:
                    newest = lm

        return {
            "count": len(artifacts),
            "total_size_bytes": total_size,
            "oldest": oldest or "",
            "newest": newest or "",
            "by_format": by_format,
        }
