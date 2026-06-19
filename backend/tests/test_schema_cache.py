"""Integration test for Redis schema cache.

Run from project root:
    python backend/tests/test_schema_cache.py
"""

import asyncio
import sys

sys.path.insert(0, "/Users/tunasonmez/projects/b2metric-aria/backend")

from dotenv import load_dotenv

load_dotenv("/Users/tunasonmez/projects/b2metric-aria/.env")

from backend.app.schema_discovery.cache import (  # noqa: E402
    get_cache_ttl,
    get_schema,
    invalidate_schema,
    set_schema,
)
from backend.app.schema_discovery.models import (  # noqa: E402
    ColumnInfo,
    ForeignKeyInfo,
    SchemaSnapshot,
    TableInfo,
)


async def main():
    ws_id = "ws_test_001"
    db_id = "db_test_001"

    # Build a sample snapshot
    snapshot = SchemaSnapshot(
        workspace_id=ws_id,
        db_config_id=db_id,
        db_type="postgresql",
        database_name="testdb",
        tables=[
            TableInfo(
                name="users",
                columns=[
                    ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                    ColumnInfo(name="email", data_type="varchar", nullable=False),
                    ColumnInfo(name="name", data_type="varchar"),
                ],
                foreign_keys=[],
            ),
            TableInfo(
                name="orders",
                columns=[
                    ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                    ColumnInfo(name="user_id", data_type="integer"),
                    ColumnInfo(name="total", data_type="numeric"),
                ],
                foreign_keys=[
                    ForeignKeyInfo(
                        source_table="orders",
                        source_column="user_id",
                        target_table="users",
                        target_column="id",
                        constraint_name="fk_orders_users",
                    ),
                ],
            ),
        ],
    )

    # 1. Store
    print("1. Storing snapshot...")
    await set_schema(snapshot, ttl_seconds=60)
    print("   Stored OK")

    # 2. Retrieve
    print("2. Retrieving snapshot...")
    retrieved = await get_schema(ws_id, db_id)
    assert retrieved is not None, "FAIL: Retrieved None"
    print(
        f"   Retrieved OK: {retrieved.table_count} tables, "
        f"{retrieved.total_columns} columns, {retrieved.total_foreign_keys} FKs"
    )

    # 3. Check TTL
    ttl = await get_cache_ttl(ws_id, db_id)
    print(f"3. TTL: {ttl}s remaining (should be ~60)")

    # 4. Tenant isolation: different workspace shouldn't see it
    other = await get_schema("ws_other_999", db_id)
    assert other is None, "FAIL: Tenant isolation broken!"
    print("4. Tenant isolation OK: different workspace sees None")

    # 5. Invalidate
    deleted = await invalidate_schema(ws_id, db_id)
    assert deleted, "FAIL: Invalidate returned False"
    print("5. Invalidate OK")

    # 6. Verify gone
    gone = await get_schema(ws_id, db_id)
    assert gone is None, "FAIL: Schema still cached after invalidate"
    print("6. Post-invalidate verification OK: schema gone")

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
