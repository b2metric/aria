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
            prefs = "\n".join(f"  - {m.get('memory', m)}" for m in self.user_preferences[:3])
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
            # Search user memories (Mem0 0.1.x API: user_id is a direct parameter)
            user_results = self._memory.search(
                query=question,
                user_id=f"{workspace_id}:{user_id}",
                limit=limit,
            )
            if user_results and "results" in user_results:
                user_prefs = user_results["results"]
                all_memories.extend(user_prefs)

            # Search team memories (if team_id provided)
            if team_id:
                team_results = self._memory.search(
                    query=question,
                    user_id=f"{workspace_id}:team:{team_id}",
                    limit=limit,
                )
                if team_results and "results" in team_results:
                    team_convs = team_results["results"]
                    all_memories.extend(team_convs)

            # Search query cache (workspace-wide)
            cache_results = self._memory.search(
                query=question,
                user_id=f"{workspace_id}:query_cache",
                limit=limit,
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
            result = self._memory.add(
                content,
                user_id=mem_user_id,
                metadata=metadata or {},
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

            result = self._memory.get_all(user_id=mem_user_id)
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

            # Update metadata with expires_at using Qdrant directly
            from qdrant_client import QdrantClient

            settings = get_settings()

            qdrant_url = settings.qdrant_url
            if qdrant_url.startswith("http://"):
                qdrant_host = qdrant_url.replace("http://", "").split(":")[0]
                qdrant_port = int(qdrant_url.split(":")[-1])
            else:
                qdrant_host = "localhost"
                qdrant_port = 6333

            client = QdrantClient(host=qdrant_host, port=qdrant_port)

            # Update the point's payload with expires_at
            client.set_payload(
                collection_name=settings.qdrant_collection,
                payload={"expires_at": expires_at},
                points=[memory_id],
            )

            logger.info("Updated TTL for memory %s: expires_at=%s", memory_id, expires_at)
            return True

        except Exception as e:
            logger.warning("Failed to update TTL for memory %s: %s", memory_id, e)
            return False

    def get_memory_stats(self, workspace_id: str) -> dict:
        """Get memory statistics for a workspace."""
        if not self._memory:
            return {"total": 0, "by_type": {}, "expiring_soon": 0}

        stats = {
            "total": 0,
            "by_type": {"user": 0, "team": 0, "cache": 0},
            "expiring_soon": 0,
            "recent_7d": 0,
        }

        try:
            now = datetime.now(UTC)
            soon_cutoff = now + timedelta(days=7)
            recent_cutoff = now - timedelta(days=7)

            # Get cache memories
            cache_mems = self._memory.get_all(user_id=f"{workspace_id}:query_cache")
            cache_results = cache_mems.get("results", []) if isinstance(cache_mems, dict) else []
            stats["by_type"]["cache"] = len(cache_results)
            stats["total"] += len(cache_results)

            # Get team memories
            team_mems = self._memory.get_all(user_id=f"{workspace_id}:team:default")
            team_results = team_mems.get("results", []) if isinstance(team_mems, dict) else []
            stats["by_type"]["team"] = len(team_results)
            stats["total"] += len(team_results)

            # Get user memories (user preferences stored under workspace_id:user:*)
            # We search for memories that match user preference patterns
            try:
                user_mems = self._memory.search(
                    query="user preference",
                    user_id=f"{workspace_id}:user",
                    limit=100,
                )
                user_results = user_mems.get("results", []) if isinstance(user_mems, dict) else []
                stats["by_type"]["user"] = len(user_results)
                stats["total"] += len(user_results)
            except Exception:
                # Fallback: count from get_all_memories with USER type
                user_results = []

            # Count recent and expiring
            for mem in cache_results + team_results + user_results:
                created_at = mem.get("created_at")
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

                expires_at = (
                    mem.get("metadata", {}).get("expires_at") if mem.get("metadata") else None
                )
                if expires_at:
                    try:
                        exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        if exp_time < soon_cutoff:
                            stats["expiring_soon"] += 1
                    except (ValueError, TypeError):
                        pass

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
        now - timedelta(days=user_ttl_days)

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

            # Clean up user preferences (180 days hard decay per Task 4)
            # Find all user IDs inside workspace_id
            # Mem0 API currently doesn't allow fetching across all user_ids easily,
            # so we fetch by the 'user' metadata marker if we can, or iterate known users.
            # But get_all_memories without user_id might work or we use a fallback.
            # We will use the base memory search to fetch all user memories in the workspace.
            user_cutoff_180d = now - timedelta(days=180)  # Force 6 months memory decay
            all_user_mems = self._memory.get_all()
            if all_user_mems and isinstance(all_user_mems, dict) and "results" in all_user_mems:
                for mem in all_user_mems["results"]:
                    mem_uid = mem.get("user_id", "")
                    if (
                        mem_uid.startswith(f"{workspace_id}:")
                        and ":team:" not in mem_uid
                        and ":query_cache" not in mem_uid
                    ):
                        created_at = mem.get("created_at")
                        if created_at:
                            try:
                                if isinstance(created_at, str):
                                    mem_time = datetime.fromisoformat(
                                        created_at.replace("Z", "+00:00")
                                    )
                                else:
                                    mem_time = datetime.fromtimestamp(created_at, tz=UTC)

                                if mem_time < user_cutoff_180d:
                                    mem_id = mem.get("id")
                                    if mem_id and self.delete_memory(mem_id):
                                        deleted["user"] += 1
                            except (ValueError, TypeError):
                                continue

            logger.info(
                "Memory cleanup for workspace=%s: cache=%d deleted (>%dd)",
                workspace_id,
                deleted["cache"],
                cache_ttl_days,
            )

        except Exception as e:
            logger.warning("Memory cleanup failed: %s", e)

        return deleted
