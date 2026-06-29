"""Memory service using Mem0 + Qdrant for user/team context and query caching.

Memory Types:
- USER: Personal preferences, frequently used tables/columns, query patterns
- TEAM: Department conventions, business definitions, metric formulas
- QUERY_CACHE: Previously executed queries with their SQL for reuse

Usage in pipeline:
1. BEFORE SQL generation: lookup() to get relevant context
2. AFTER successful query: store() to cache the result
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

try:
    from mem0 import Memory
except ImportError:  # mem0ai not installed — memory features degrade to a no-op
    Memory = None  # type: ignore[assignment, misc]

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


# ── Memory decay / relevance scoring (Sprint 15 Task 5) ──────────────────────
# User preferences previously used a hard 180-day delete. We now score each
# entry by a recency- and usage-weighted relevance and only purge long-cold
# entries, so a frequently-recalled old preference outlives an untouched one.
#
# Recency decays exponentially with a half-life; frequent recall (``use_count``
# in metadata) extends the effective half-life so it ages more slowly. With
# 0 uses, the score crosses MEMORY_PURGE_THRESHOLD at ≈ half_life·log2(1/thresh)
# ≈ 45·4.3 ≈ 195 days — close to the old 180-day cutoff, but graded.
MEMORY_HALF_LIFE_DAYS = 45.0
MEMORY_PURGE_THRESHOLD = 0.05


def relevance_score(
    age_days: float,
    use_count: int = 0,
    *,
    half_life_days: float = MEMORY_HALF_LIFE_DAYS,
) -> float:
    """Recency- and usage-weighted relevance in ``(0, 1]``.

    ``age_days`` 0 → 1.0; one half-life → 0.5. Each prior recall slows aging by
    extending the effective half-life (saturating, via ``log1p``), so a
    well-used memory scores higher than an untouched one of the same age.
    """
    age_days = max(0.0, age_days)
    effective_age = age_days / (1.0 + 0.5 * math.log1p(max(0, use_count)))
    return 0.5 ** (effective_age / half_life_days)


def _parse_created_at(value: Any) -> datetime | None:
    """Parse a Mem0 ``created_at`` (ISO string or epoch) into aware UTC datetime."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromtimestamp(value, tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def should_purge_user_memory(mem: dict, now: datetime) -> bool:
    """Whether a user-preference entry has decayed below the purge threshold.

    Replaces the old hard 180-day cutoff. Entries with an unparseable/missing
    ``created_at`` are never purged (we don't blind-delete unknown-age data).
    """
    created = _parse_created_at(mem.get("created_at"))
    if created is None:
        return False
    age_days = (now - created).total_seconds() / 86400.0
    use_count = int((mem.get("metadata") or {}).get("use_count", 0) or 0)
    return relevance_score(age_days, use_count) < MEMORY_PURGE_THRESHOLD


def _memory_relevance(mem: dict, now: datetime) -> float:
    """Relevance score for ranking a memory entry; unknown age → treated as fresh."""
    created = _parse_created_at(mem.get("created_at"))
    age_days = (now - created).total_seconds() / 86400.0 if created else 0.0
    use_count = int((mem.get("metadata") or {}).get("use_count", 0) or 0)
    return relevance_score(age_days, use_count)


class MemoryType(StrEnum):
    """Memory scope types."""

    USER = "user"  # Personal: preferences, favorite tables
    TEAM = "team"  # Department: business definitions, conventions
    QUERY_CACHE = "query"  # Query cache: NL question → SQL mapping


@dataclass
class MemoryContext:
    """Context retrieved from memory for SQL generation."""

    user_preferences: list[dict]  # User's past queries, preferred columns
    team_conventions: list[dict]  # Team's business rules, metric definitions
    similar_queries: list[dict]  # Previously executed similar queries
    raw_memories: list[dict]  # All raw memory entries for debugging

    def to_prompt_context(self) -> str:
        """Format memory context for LLM prompt injection."""
        parts = []

        if self.user_preferences:
            # Up to 5: room for both relevance-ranked matches and the standing
            # directives that `lookup` injects proactively (Sprint 15 Task 4).
            prefs = "\n".join(f"  - {m.get('memory', m)}" for m in self.user_preferences[:5])
            parts.append(f"User Preferences:\n{prefs}")

        if self.team_conventions:
            convs = "\n".join(f"  - {m.get('memory', m)}" for m in self.team_conventions[:3])
            parts.append(f"Team Conventions:\n{convs}")

        if self.similar_queries:
            queries = []
            for q in self.similar_queries[:2]:
                mem = q.get("memory", "")
                queries.append(f"  - {mem[:200]}")
            parts.append("Similar Past Queries:\n" + "\n".join(queries))

        return "\n\n".join(parts) if parts else ""

    @property
    def has_context(self) -> bool:
        """Check if any useful context was found."""
        return bool(self.user_preferences or self.team_conventions or self.similar_queries)


class MemoryService:
    """Mem0-backed memory service for ARIA.

    Provides contextual recall for SQL generation based on:
    - User's past queries and preferences
    - Team's business conventions
    - Similar previously executed queries
    """

    _instance: MemoryService | None = None

    def __init__(self) -> None:
        """Initialize Mem0 with Qdrant backend."""
        settings = get_settings()

        # Parse Qdrant URL
        qdrant_url = settings.qdrant_url
        if qdrant_url.startswith("http://"):
            qdrant_host = qdrant_url.replace("http://", "").split(":")[0]
            qdrant_port = int(qdrant_url.split(":")[-1])
        else:
            qdrant_host = "localhost"
            qdrant_port = 6333

        # Mem0 config with Qdrant vector store
        # Use OpenAI provider pointing to LiteLLM proxy for both LLM and embeddings
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": qdrant_host,
                    "port": qdrant_port,
                    "collection_name": settings.qdrant_collection,
                    "embedding_model_dims": 3072,  # Gemini embedding-001 outputs 3072 dims
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": settings.llm_model,
                    "openai_base_url": settings.litellm_api_base,
                    "api_key": settings.litellm_api_key or "sk-placeholder",
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "gemini-embedding",  # Use Gemini via LiteLLM (OpenAI quota exceeded)
                    "embedding_dims": 3072,  # Gemini embedding-001 outputs 3072 dims
                    "openai_base_url": settings.litellm_api_base,
                    "api_key": settings.litellm_api_key or "***",
                },
            },
        }

        try:
            if Memory is None:
                raise RuntimeError("mem0 package not installed")
            self._memory = Memory.from_config(config)
            logger.info(
                "MemoryService initialized: qdrant=%s:%d, collection=%s",
                qdrant_host,
                qdrant_port,
                settings.qdrant_collection,
            )
        except Exception as e:
            logger.warning("Failed to initialize Mem0, using fallback: %s", e)
            self._memory = None

    @classmethod
    def get_instance(cls) -> MemoryService:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def lookup(
        self,
        question: str,
        user_id: str,
        workspace_id: str,
        team_id: str | None = None,
        limit: int = 5,
    ) -> MemoryContext:
        """Retrieve relevant context for a question.

        Args:
            question: Natural language question
            user_id: User identifier
            workspace_id: Workspace/customer identifier
            team_id: Optional team/department identifier
            limit: Max memories per category

        Returns:
            MemoryContext with relevant memories for SQL generation
        """
        if not self._memory:
            return MemoryContext([], [], [], [])

        user_prefs = []
        team_convs = []
        similar_queries = []
        all_memories = []

        try:
            # Search user memories. mem0 2.x: the scope goes inside ``filters=``
            # (a top-level ``user_id=`` raises "not supported in search()") and the
            # cap is ``top_k`` rather than ``limit``.
            user_results = self._memory.search(
                query=question,
                filters={"user_id": f"{workspace_id}:{user_id}"},
                top_k=limit,
            )
            if user_results and "results" in user_results:
                user_prefs = user_results["results"]
                all_memories.extend(user_prefs)

            # Proactively inject standing preferences. Semantic search only
            # surfaces a directive ("User associates TOPUP_AMOUNT with revenue")
            # when the question wording is similar; standing directives must feed
            # SQL generation regardless. Pull all USER-type prefs and append the
            # ones the semantic search missed (deduped by id, then by text).
            standing_prefs = self.get_user_preferences(workspace_id=workspace_id, user_id=user_id)
            seen_ids = {p.get("id") for p in user_prefs if p.get("id")}
            seen_text = {p.get("memory") or "" for p in user_prefs}
            extras = [
                p
                for p in standing_prefs
                if p.get("id") not in seen_ids and (p.get("memory") or "") not in seen_text
            ]
            if extras:
                user_prefs = user_prefs + extras
                all_memories.extend(extras)

            # Search team memories (if team_id provided)
            if team_id:
                team_results = self._memory.search(
                    query=question,
                    filters={"user_id": f"{workspace_id}:team:{team_id}"},
                    top_k=limit,
                )
                if team_results and "results" in team_results:
                    # Only approved conventions feed the LLM context. Entries with
                    # no `status` are legacy and treated as approved; `pending` /
                    # `rejected` are withheld until an admin/team_lead approves.
                    team_convs = [
                        r
                        for r in team_results["results"]
                        if ((r.get("metadata") or {}).get("status") or "approved") == "approved"
                    ]
                    all_memories.extend(team_convs)

            # Search query cache (workspace-wide)
            cache_results = self._memory.search(
                query=question,
                filters={"user_id": f"{workspace_id}:query_cache"},
                top_k=limit,
            )
            if cache_results and "results" in cache_results:
                similar_queries = cache_results["results"]
                all_memories.extend(similar_queries)

            logger.debug(
                "Memory lookup for '%s': user=%d, team=%d, cache=%d",
                question[:50],
                len(user_prefs),
                len(team_convs),
                len(similar_queries),
            )

        except Exception as e:
            logger.warning("Memory lookup failed: %s", e)

        return MemoryContext(
            user_preferences=user_prefs,
            team_conventions=team_convs,
            similar_queries=similar_queries,
            raw_memories=all_memories,
        )

    def get_user_preferences(
        self,
        *,
        workspace_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Return the user's standing preferences (USER-type memories).

        Unlike :meth:`lookup`'s semantic search, this returns directives
        unconditionally (regardless of the current question) so they can be
        *proactively* injected into SQL generation — e.g. a stored
        "User associates TOPUP_AMOUNT with revenue" still applies when the user
        asks about "churn" or "growth".
        """
        if not self._memory:
            return []
        try:
            result = self._memory.get_all(filters={"user_id": f"{workspace_id}:{user_id}"})
            rows = result.get("results", []) if isinstance(result, dict) else []
            # Rank by relevance (recency + usage) so the freshest / most-used
            # standing directives win the prompt-context slice (Sprint 15 Task 5).
            now = datetime.now(UTC)
            rows.sort(key=lambda m: _memory_relevance(m, now), reverse=True)
            return rows[:limit]
        except Exception as e:
            logger.warning("Failed to fetch user preferences: %s", e)
            return []

    def store(
        self,
        content: str,
        memory_type: MemoryType,
        user_id: str,
        workspace_id: str,
        team_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Store a new memory entry.

        Args:
            content: Memory content (e.g., "User prefers TOPUP_AMOUNT for revenue")
            memory_type: Type of memory (USER, TEAM, QUERY_CACHE)
            user_id: User identifier
            workspace_id: Workspace/customer identifier
            team_id: Team identifier (required for TEAM type)
            metadata: Optional metadata (table, columns, sql, etc.)

        Returns:
            Memory ID if successful, None otherwise
        """
        if not self._memory:
            return None

        # Build the user_id based on memory type
        if memory_type == MemoryType.USER:
            mem_user_id = f"{workspace_id}:{user_id}"
        elif memory_type == MemoryType.TEAM:
            if not team_id:
                logger.warning("team_id required for TEAM memory type")
                return None
            mem_user_id = f"{workspace_id}:team:{team_id}"
        else:  # QUERY_CACHE
            mem_user_id = f"{workspace_id}:query_cache"

        try:
            # infer=False stores the content verbatim. Mem0 2.x defaults to
            # infer=True (LLM fact-extraction), which silently drops short,
            # imperative entries like conventions/preferences → no id returned.
            result = self._memory.add(
                content,
                user_id=mem_user_id,
                metadata=metadata or {},
                infer=False,
            )
            # Mem0 returns {'results': [{'id': '...', 'memory': '...', 'event': 'ADD'}]}
            results = result.get("results", []) if isinstance(result, dict) else []
            memory_id = results[0].get("id") if results else None
            logger.debug(
                "Stored %s memory for %s: %s",
                memory_type.value,
                mem_user_id,
                content[:50],
            )
            return memory_id
        except Exception as e:
            logger.warning("Failed to store memory: %s", e)
            return None

    def store_query(
        self,
        question: str,
        sql: str,
        table: str,
        user_id: str,
        workspace_id: str,
        row_count: int = 0,
    ) -> str | None:
        """Store a successful query for future reuse.

        This is a convenience method for caching NL → SQL mappings.

        Args:
            question: Original natural language question
            sql: Generated SQL query
            table: Primary table used
            user_id: User who executed the query
            workspace_id: Workspace identifier
            row_count: Number of rows returned

        Returns:
            Memory ID if successful
        """
        content = f"Question: {question}\nSQL: {sql}\nTable: {table}"
        metadata = {
            "question": question,
            "sql": sql,
            "table": table,
            "user_id": user_id,
            "row_count": row_count,
        }
        return self.store(
            content=content,
            memory_type=MemoryType.QUERY_CACHE,
            user_id=user_id,
            workspace_id=workspace_id,
            metadata=metadata,
        )

    def store_user_preference(
        self,
        preference: str,
        user_id: str,
        workspace_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Store a user preference (convenience method).

        Examples:
            - "User prefers monthly aggregation for revenue queries"
            - "User frequently queries fct_prep_recharge table"
            - "User uses TOPUP_AMOUNT for amount-related queries"
        """
        return self.store(
            content=preference,
            memory_type=MemoryType.USER,
            user_id=user_id,
            workspace_id=workspace_id,
            metadata=metadata,
        )

    def get_all_memories(
        self,
        user_id: str,
        workspace_id: str,
        memory_type: MemoryType | None = None,
    ) -> list[dict]:
        """Get all memories for a user (for debugging/admin).

        Args:
            user_id: User identifier
            workspace_id: Workspace identifier
            memory_type: Optional filter by type

        Returns:
            List of memory entries
        """
        if not self._memory:
            return []

        try:
            if memory_type == MemoryType.USER:
                mem_user_id = f"{workspace_id}:{user_id}"
            elif memory_type == MemoryType.TEAM:
                mem_user_id = f"{workspace_id}:team:{user_id}"
            elif memory_type == MemoryType.QUERY_CACHE:
                mem_user_id = f"{workspace_id}:query_cache"
            else:
                mem_user_id = f"{workspace_id}:{user_id}"

            result = self._memory.get_all(filters={"user_id": mem_user_id})
            return result.get("results", []) if isinstance(result, dict) else []
        except Exception as e:
            logger.warning("Failed to get memories: %s", e)
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory entry.

        Args:
            memory_id: Memory identifier to delete

        Returns:
            True if deleted successfully
        """
        if not self._memory:
            return False

        try:
            self._memory.delete(memory_id)
            return True
        except Exception as e:
            logger.warning("Failed to delete memory %s: %s", memory_id, e)
            return False

    def _qdrant_client(self) -> tuple[Any, str]:
        """Build a direct Qdrant client + collection name.

        Used for operations Mem0's API can't express — payload edits and
        workspace-wide scrolls (Mem0 0.1.x ``get_all()`` requires a user_id).
        """
        from qdrant_client import QdrantClient

        settings = get_settings()
        url = settings.qdrant_url
        if url.startswith("http://"):
            host = url.replace("http://", "").split(":")[0]
            port = int(url.split(":")[-1])
        else:
            host, port = "localhost", 6333
        return QdrantClient(host=host, port=port), settings.qdrant_collection

    def set_memory_status(
        self,
        memory_id: str,
        new_status: str,
        *,
        workspace_id: str,
        team_id: str,
    ) -> bool:
        """Set the approval status (pending/approved/rejected) of a team convention.

        Locates the entry via ``get_all`` (Mem0 2.x ``get(vector_id=...)`` is
        unreliable for these points, whereas ``get_all`` works), then re-writes
        it via ``update`` preserving the text and merging ``status`` into the
        metadata. Used by the team-conventions approval workflow.
        """
        if not self._memory:
            return False
        try:
            mem_user_id = f"{workspace_id}:team:{team_id}"
            result = self._memory.get_all(filters={"user_id": mem_user_id})
            rows = result.get("results", []) if isinstance(result, dict) else []
            entry = next((r for r in rows if r.get("id") == memory_id), None)
            if not entry:
                return False
            text = entry.get("memory") or entry.get("data") or ""
            metadata = dict(entry.get("metadata") or {})
            metadata["status"] = new_status
            # Mem0 2.x single-entry update()/get() (vector_store.get by id) are
            # unreliable for these points, but get_all/delete/add all work — so
            # re-create the entry with the new status metadata.
            self._memory.delete(memory_id)
            self._memory.add(text, user_id=mem_user_id, metadata=metadata, infer=False)
            return True
        except Exception as e:
            logger.warning("Failed to set status on memory %s: %s", memory_id, e)
            return False

    def update_memory_ttl(
        self,
        memory_id: str,
        ttl_days: int | None,
    ) -> bool:
        """Update TTL for a specific memory entry.

        Args:
            memory_id: Memory identifier
            ttl_days: Days until expiration (None = never expire)

        Returns:
            True if updated successfully
        """
        if not self._memory:
            return False

        try:
            # Calculate expires_at timestamp
            if ttl_days is None:
                expires_at = None  # Never expires
            elif ttl_days == 0:
                # Immediate deletion
                return self.delete_memory(memory_id)
            else:
                expires_at = (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat()

            # Update the point's payload with expires_at using Qdrant directly
            client, collection = self._qdrant_client()
            client.set_payload(
                collection_name=collection,
                payload={"expires_at": expires_at},
                points=[memory_id],
            )

            logger.info("Updated TTL for memory %s: expires_at=%s", memory_id, expires_at)
            return True

        except Exception as e:
            logger.warning("Failed to update TTL for memory %s: %s", memory_id, e)
            return False

    def get_memory_stats(self, workspace_id: str) -> dict:
        """Get memory statistics for a workspace.

        Counts by scanning Qdrant directly and classifying each point by its
        namespaced ``user_id`` payload (``{ws}:{user}`` / ``{ws}:team:{id}`` /
        ``{ws}:query_cache``). The previous get_all/search used LITERAL prefixes
        (``{ws}:team:default`` / ``{ws}:user``) that matched almost nothing —
        mem0's get_all requires an exact user_id, not a prefix — so team/user
        counts read ~0. The scroll pattern mirrors cleanup_expired_memories.
        """
        stats = {
            "total": 0,
            "by_type": {"user": 0, "team": 0, "cache": 0},
            "expiring_soon": 0,
            "recent_7d": 0,
        }
        if not self._memory:
            return stats

        try:
            now = datetime.now(UTC)
            soon_cutoff = now + timedelta(days=7)
            recent_cutoff = now - timedelta(days=7)
            prefix = f"{workspace_id}:"

            client, collection = self._qdrant_client()
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=collection,
                    limit=256,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset,
                )
                for point in points:
                    payload = point.payload or {}
                    uid = payload.get("user_id", "")
                    if not uid.startswith(prefix):
                        continue

                    if uid.endswith(":query_cache"):
                        mem_type = "cache"
                    elif ":team:" in uid:
                        mem_type = "team"
                    else:
                        mem_type = "user"
                    stats["by_type"][mem_type] += 1
                    stats["total"] += 1

                    created_at = payload.get("created_at")
                    if created_at:
                        try:
                            if isinstance(created_at, str):
                                mem_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            else:
                                mem_time = datetime.fromtimestamp(created_at, tz=UTC)
                            if mem_time > recent_cutoff:
                                stats["recent_7d"] += 1
                        except (ValueError, TypeError):
                            pass

                    expires_at = payload.get("expires_at")
                    if expires_at:
                        try:
                            exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                            if exp_time < soon_cutoff:
                                stats["expiring_soon"] += 1
                        except (ValueError, TypeError):
                            pass

                if offset is None:
                    break

        except Exception as e:
            logger.warning("Failed to get memory stats: %s", e)

        return stats

    def cleanup_expired_memories(
        self,
        workspace_id: str,
        cache_ttl_days: int = 7,
        user_ttl_days: int = 90,
    ) -> dict[str, int]:
        """Clean up expired memories based on retention policy.

        Retention policy (configurable via Tenant Config):
        - QUERY_CACHE: 7 days (default) - stale SQL mappings
        - USER: 90 days (default) - old preferences
        - TEAM: ∞ (never expires) - institutional knowledge

        Args:
            workspace_id: Workspace identifier
            cache_ttl_days: Days to keep query cache (default: 7)
            user_ttl_days: Days to keep user memories (default: 90)

        Returns:
            Dict with counts of deleted memories per type
        """
        if not self._memory:
            return {"cache": 0, "user": 0}

        now = datetime.now(UTC)
        cache_cutoff = now - timedelta(days=cache_ttl_days)
        # user_ttl_days retained for API/endpoint compatibility; user-preference
        # retention is now governed by relevance-scoring decay, not a fixed cutoff.

        deleted = {"cache": 0, "user": 0}

        try:
            # Clean up query cache
            cache_memories = self.get_all_memories(
                user_id="query_cache",
                workspace_id=workspace_id,
                memory_type=MemoryType.QUERY_CACHE,
            )
            for mem in cache_memories:
                created_at = mem.get("created_at")
                if created_at:
                    # Parse ISO format or timestamp
                    if isinstance(created_at, str):
                        try:
                            mem_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                    else:
                        mem_time = datetime.fromtimestamp(created_at, tz=UTC)

                    if mem_time < cache_cutoff:
                        mem_id = mem.get("id")
                        if mem_id and self.delete_memory(mem_id):
                            deleted["cache"] += 1

            # Clean up user preferences via relevance-scoring decay (Sprint 15
            # Task 5) — only long-cold entries (score < MEMORY_PURGE_THRESHOLD)
            # are purged, so a frequently-recalled old preference survives where
            # an untouched one decays away. Mem0 0.1.x get_all() requires a
            # user_id, so a workspace-wide sweep scrolls Qdrant directly and
            # scopes to this workspace's USER namespace (skipping team/cache).
            client, collection = self._qdrant_client()
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=collection,
                    limit=256,
                    with_payload=True,
                    offset=offset,
                )
                for point in points:
                    payload = point.payload or {}
                    uid = payload.get("user_id", "")
                    if not (
                        uid.startswith(f"{workspace_id}:")
                        and ":team:" not in uid
                        and ":query_cache" not in uid
                    ):
                        continue
                    # Mem0 stores metadata flat in the payload, so pass the whole
                    # payload as `metadata` for the use_count lookup.
                    mem = {"created_at": payload.get("created_at"), "metadata": payload}
                    if should_purge_user_memory(mem, now) and self.delete_memory(str(point.id)):
                        deleted["user"] += 1
                if offset is None:
                    break

            logger.info(
                "Memory cleanup for workspace=%s: cache=%d deleted (>%dd)",
                workspace_id,
                deleted["cache"],
                cache_ttl_days,
            )

        except Exception as e:
            logger.warning("Memory cleanup failed: %s", e)

        return deleted
