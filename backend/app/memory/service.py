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
from enum import Enum
from typing import Any

from mem0 import Memory

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
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
            parts.append(f"Similar Past Queries:\n" + "\n".join(queries))

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

    _instance: "MemoryService | None" = None

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
    def get_instance(cls) -> "MemoryService":
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
            # Search user memories (Mem0 v0.1.x uses filters instead of user_id)
            user_results = self._memory.search(
                query=question,
                filters={"user_id": f"{workspace_id}:{user_id}"},
                limit=limit,
            )
            if user_results and "results" in user_results:
                user_prefs = user_results["results"]
                all_memories.extend(user_prefs)

            # Search team memories (if team_id provided)
            if team_id:
                team_results = self._memory.search(
                    query=question,
                    filters={"user_id": f"{workspace_id}:team:{team_id}"},
                    limit=limit,
                )
                if team_results and "results" in team_results:
                    team_convs = team_results["results"]
                    all_memories.extend(team_convs)

            # Search query cache (workspace-wide)
            cache_results = self._memory.search(
                query=question,
                filters={"user_id": f"{workspace_id}:query_cache"},
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
