"""Additional edge case tests for Redis schema cache."""

import asyncio
import sys

sys.path.insert(0, "/Users/tunasonmez/projects/b2metric-aria/backend")

from dotenv import load_dotenv

load_dotenv("/Users/tunasonmez/projects/b2metric-aria/.env")

from backend.app.schema_discovery.cache import (  # noqa: E402
    get_schema,
    invalidate_workspace,
    set_schema,
)
from backend.app.schema_discovery.models import (  # noqa: E402
    ColumnInfo,
    SchemaSnapshot,
    TableInfo,
)


async def main():
    errors = []

    # ── Test: workspace-wide invalidation ──
    ws = "ws_edge_001"
    snapshots = []
    for i in range(3):
        s = SchemaSnapshot(
            workspace_id=ws,
            db_config_id=f"db_{i}",
            db_type="postgresql",
            database_name=f"testdb_{i}",
            tables=[
                TableInfo(
                    name="t",
                    columns=[ColumnInfo(name="id", data_type="integer", is_primary_key=True)],
                )
            ],
        )
        await set_schema(s, ttl_seconds=300)
        snapshots.append(s)

    # Verify all 3 exist
    for s in snapshots:
        r = await get_schema(s.workspace_id, s.db_config_id)
        if r is None:
            errors.append(f"Snapshot {s.db_config_id} not found before invalidation")

    # Invalidate workspace
    deleted = await invalidate_workspace(ws)
    if deleted != 3:
        errors.append(f"Expected 3 keys deleted, got {deleted}")

    # Verify all gone
    for s in snapshots:
        r = await get_schema(s.workspace_id, s.db_config_id)
        if r is not None:
            errors.append(f"Snapshot {s.db_config_id} still exists after workspace invalidation")

    # ── Test: different workspace unaffected ──
    other_ws = "ws_edge_002"
    other = SchemaSnapshot(
        workspace_id=other_ws,
        db_config_id="db_x",
        db_type="mysql",
        database_name="otherdb",
        tables=[],
    )
    await set_schema(other, ttl_seconds=300)

    # Invalidate ws_edge_001 again (should be 0)
    deleted2 = await invalidate_workspace(ws)
    if deleted2 != 0:
        errors.append(f"Expected 0 keys deleted for empty workspace, got {deleted2}")

    # Verify ws_edge_002 still exists
    r = await get_schema(other_ws, "db_x")
    if r is None:
        errors.append("Other workspace snapshot was incorrectly deleted")

    # Cleanup
    await invalidate_workspace(other_ws)

    # ── Test: corrupted cache entry ──
    import redis.asyncio as aioredis

    from backend.app.core.config import get_settings

    settings = get_settings()
    r_client = await aioredis.from_url(str(settings.redis_url), decode_responses=True)
    try:
        corrupt_key = "aria:schema:ws_corrupt:db_corrupt"
        await r_client.setex(corrupt_key, 60, "this is not valid json {{{")
        result = await get_schema("ws_corrupt", "db_corrupt")
        if result is not None:
            errors.append("Corrupted cache should return None")
        await r_client.delete(corrupt_key)
    finally:
        await r_client.aclose()

    # ── Report ──
    if errors:
        print("FAILURES:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("=== ALL EDGE CASE TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
