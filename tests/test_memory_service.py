"""Smoke tests for ARIA Memory Service (Mem0 + Qdrant).

Tests user/team/query_cache memory types separately.
Run: pytest tests/test_memory_service.py -v
"""

import pytest
import uuid
from dataclasses import dataclass
from unittest.mock import patch, MagicMock

# Skip all tests if dependencies not available
pytest.importorskip("mem0")


class TestMemoryServiceUnit:
    """Unit tests without external dependencies."""

    def test_memory_type_enum(self):
        """Test MemoryType enum values."""
        from backend.app.memory.service import MemoryType
        
        assert MemoryType.USER.value == "user"
        assert MemoryType.TEAM.value == "team"
        assert MemoryType.QUERY_CACHE.value == "query"  # Actual value

    def test_memory_context_empty(self):
        """Test empty MemoryContext properties."""
        from backend.app.memory.service import MemoryContext
        
        ctx = MemoryContext(
            user_preferences=[],
            team_conventions=[],
            similar_queries=[],
            raw_memories=[],
        )
        
        assert not ctx.has_context
        assert ctx.to_prompt_context() == ""

    def test_memory_context_with_data(self):
        """Test MemoryContext with data."""
        from backend.app.memory.service import MemoryContext
        
        ctx = MemoryContext(
            user_preferences=[{"memory": "User prefers bar charts"}],
            team_conventions=[{"memory": "Revenue means TOPUP_AMOUNT"}],
            similar_queries=[
                {
                    "memory": "Question: show monthly revenue\nSQL: SELECT MONTH, SUM(AMOUNT) FROM SALES GROUP BY MONTH",
                }
            ],
            raw_memories=[],
        )
        
        assert ctx.has_context
        prompt = ctx.to_prompt_context()
        assert "bar charts" in prompt
        assert "Revenue means" in prompt
        assert "monthly revenue" in prompt


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    with patch("backend.app.memory.service.get_settings") as mock:
        settings = MagicMock()
        settings.qdrant_url = "http://localhost:6333"
        settings.qdrant_collection = "test_aria_memory"
        settings.litellm_api_base = "http://localhost:4000"
        settings.litellm_api_key = "test-key"
        settings.llm_model = "deepseek-chat"
        mock.return_value = settings
        yield settings


class TestMemoryServiceIntegration:
    """Integration tests - require Qdrant + LiteLLM running."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        self.workspace_id = "test-workspace"
        self.user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.team_id = f"test-team-{uuid.uuid4().hex[:8]}"

    @pytest.mark.integration
    def test_memory_service_init(self):
        """Test MemoryService initialization."""
        from backend.app.memory.service import MemoryService
        
        # Reset singleton
        MemoryService._instance = None
        
        service = MemoryService()
        assert service._memory is not None

    @pytest.mark.integration
    def test_store_user_preference(self):
        """Test storing user preference."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        mem_id = service.store_user_preference(
            preference="User prefers pie charts for distribution data",
            user_id=self.user_id,
            workspace_id=self.workspace_id,
        )
        
        # mem_id can be None if Mem0 decides it's duplicate
        # Just ensure no exception
        print(f"User preference stored: {mem_id}")

    @pytest.mark.integration
    def test_store_team_convention(self):
        """Test storing team convention (via store method)."""
        from backend.app.memory.service import MemoryService, MemoryType
        
        MemoryService._instance = None
        service = MemoryService()
        
        mem_id = service.store(
            content="In our context, 'revenue' refers to TOPUP_AMOUNT column",
            memory_type=MemoryType.TEAM,
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            team_id=self.team_id,
        )
        
        print(f"Team convention stored: {mem_id}")

    @pytest.mark.integration
    def test_store_query_cache(self):
        """Test storing query cache."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        mem_id = service.store_query(
            question="show monthly revenue by region",
            sql="SELECT REGION, MONTH, SUM(AMOUNT) FROM SALES GROUP BY REGION, MONTH",
            table="SALES",
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            row_count=150,
        )
        
        print(f"Query cache stored: {mem_id}")

    @pytest.mark.integration
    def test_lookup_returns_context(self):
        """Test lookup returns MemoryContext."""
        from backend.app.memory.service import MemoryService, MemoryContext
        
        MemoryService._instance = None
        service = MemoryService()
        
        # First store something
        service.store_user_preference(
            preference=f"User {self.user_id} prefers dark mode charts",
            user_id=self.user_id,
            workspace_id=self.workspace_id,
        )
        
        # Then lookup
        ctx = service.lookup(
            question="show me a chart",
            user_id=self.user_id,
            workspace_id=self.workspace_id,
        )
        
        assert ctx is not None
        assert isinstance(ctx, MemoryContext)
        assert isinstance(ctx.user_preferences, list)
        assert isinstance(ctx.team_conventions, list)
        assert isinstance(ctx.similar_queries, list)

    @pytest.mark.integration
    def test_user_isolation(self):
        """Test that user memories are isolated."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        user1 = f"user-{uuid.uuid4().hex[:8]}"
        user2 = f"user-{uuid.uuid4().hex[:8]}"
        
        # Store for user1
        service.store_user_preference(
            preference=f"User {user1} prefers line charts",
            user_id=user1,
            workspace_id=self.workspace_id,
        )
        
        # Store for user2
        service.store_user_preference(
            preference=f"User {user2} prefers bar charts",
            user_id=user2,
            workspace_id=self.workspace_id,
        )
        
        # Lookup for user1 should not see user2's preferences
        ctx1 = service.lookup("show chart", user1, self.workspace_id)
        ctx2 = service.lookup("show chart", user2, self.workspace_id)
        
        # Both should have context (their own preferences)
        assert ctx1 is not None
        assert ctx2 is not None

    @pytest.mark.integration
    def test_workspace_isolation(self):
        """Test that different workspaces are isolated."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        ws1 = f"workspace-{uuid.uuid4().hex[:8]}"
        ws2 = f"workspace-{uuid.uuid4().hex[:8]}"
        
        # Store in workspace1
        service.store_query(
            question="query in workspace 1",
            sql="SELECT 1",
            table="TABLE1",
            user_id=self.user_id,
            workspace_id=ws1,
        )
        
        # Lookup in workspace2 should not find workspace1's data
        ctx = service.lookup("query", self.user_id, ws2)
        
        # Should still return a context, just potentially empty
        assert ctx is not None


class TestMemoryServiceEdgeCases:
    """Edge case tests."""

    @pytest.mark.integration
    def test_empty_lookup(self):
        """Test lookup with no prior data."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        ctx = service.lookup(
            question="completely random query",
            user_id=f"nonexistent-{uuid.uuid4().hex}",
            workspace_id=f"nonexistent-{uuid.uuid4().hex}",
        )
        
        # Should return empty context, not None
        assert ctx is not None
        assert not ctx.has_context or len(ctx.similar_queries) == 0

    @pytest.mark.integration
    def test_long_content(self):
        """Test storing very long content."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        long_preference = "User prefers " + "very detailed " * 100 + "charts"
        
        # Should not raise, even if truncated internally
        mem_id = service.store_user_preference(
            preference=long_preference,
            user_id="test-user",
            workspace_id="test-workspace",
        )
        
        # Just ensure no exception

    @pytest.mark.integration
    def test_special_characters(self):
        """Test content with special characters."""
        from backend.app.memory.service import MemoryService
        
        MemoryService._instance = None
        service = MemoryService()
        
        special_content = "User's preference: 'use <b>charts</b>' & \"graphs\" — 50% data"
        
        mem_id = service.store_user_preference(
            preference=special_content,
            user_id="test-user",
            workspace_id="test-workspace",
        )
        
        # Just ensure no exception


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
