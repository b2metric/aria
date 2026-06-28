#!/usr/bin/env python3
"""extract-db-metadata.py — offline DB metadata extractor for selected tables.

Run this on the VPN-connected box (which has the ARIA repo + venv AND network
reach to the customer Oracle). It connects to the live DB and, for ONLY the
tables you name, extracts:

  - column metadata (name, data_type, nullable, is_pk)
  - low-cardinality enum DISTINCT values (the "Bundles not Bundle" fix)
  - N sample rows (skippable with --no-sample-data; treat output as sensitive)
  - row count (ALL_TABLES.NUM_ROWS)
  - foreign-key relationships

…and writes ONE JSON file. Copy that JSON back (remote desktop / scp), then
feed the vault with it via  POST /api/workspaces/vault/import-metadata  (the
JSON shape is consumable by parse_json_metadata + inject_enum_block).

This decouples the heavy per-table introspection (~thousands of queries over
VPN for 500 tables) from the live request path, and lets you review the
artifact before it touches the vault.

Reuses ARIA modules (no oracledb re-impl): get_executor / DBConfig and the
enum-sampler helpers. Requires PYTHONPATH to include the repo root.

Usage:
    PYTHONPATH=. python scripts/extract-db-metadata.py \
        --host MIS-DWH.STC.COM.KW --port 1521 --service stcdw \
        --user COMMBI_PROD --password '***' --owner COMMBI_PROD \
        --tables FCT_PREP_RECHARGE,FCT_PREP_PROVISION \
        --out db-metadata-stc.json

    # or a file with one table per line:
    PYTHONPATH=. python scripts/extract-db-metadata.py ... --tables-file active_tables.txt

Secrets: every flag falls back to an env var (ORA_HOST/ORA_PORT/ORA_SERVICE/
ORA_USER/ORA_PASSWORD/ORA_OWNER) so the password need not appear in argv.

Exit codes: 0 = all tables ok; 1 = config/connection error; 2 = partial
(some tables failed; file still written with an `errors` array).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("extract-db-metadata")

SCHEMA_VERSION = "1.0"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract DB metadata for selected tables.")
    p.add_argument("--host", default=os.environ.get("ORA_HOST"))
    p.add_argument("--port", type=int, default=int(os.environ.get("ORA_PORT", "1521")))
    p.add_argument("--service", default=os.environ.get("ORA_SERVICE"),
                   help="Oracle service name (DSN = host:port/service)")
    p.add_argument("--user", default=os.environ.get("ORA_USER"))
    p.add_argument("--password", default=os.environ.get("ORA_PASSWORD"))
    p.add_argument("--owner", default=os.environ.get("ORA_OWNER"),
                   help="Schema owner (defaults to --user uppercased)")
    p.add_argument("--tables", help="Comma-separated table names")
    p.add_argument("--tables-file", help="File with table names (one per line or comma-separated)")
    p.add_argument("--max-cardinality", type=int, default=50,
                   help="Skip enum sampling for columns with more distinct values")
    p.add_argument("--sample-rows", type=int, default=5, help="Sample rows per table")
    p.add_argument("--no-sample-data", action="store_true",
                   help="Skip raw sample rows entirely (PII-safe output)")
    p.add_argument("--out", help="Output JSON path (default db-metadata-<owner>-<date>.json)")
    return p.parse_args()


def _load_table_list(args: argparse.Namespace) -> list[str]:
    names: list[str] = []
    if args.tables:
        names += [t.strip() for t in args.tables.split(",") if t.strip()]
    if args.tables_file:
        with open(args.tables_file, encoding="utf-8") as f:
            raw = f.read()
        names += [t.strip() for chunk in raw.splitlines() for t in chunk.split(",") if t.strip()]
    # de-dup, preserve order, uppercase (Oracle convention)
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        u = n.upper()
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ── Oracle SQL (ALL_* with owner filter — owner may differ from connect user) ──
_COLUMNS_SQL = """
SELECT column_name, data_type,
       CASE WHEN nullable = 'Y' THEN 'YES' ELSE 'NO' END AS is_nullable,
       column_id
FROM ALL_TAB_COLUMNS
WHERE owner = :owner AND table_name = :t
ORDER BY column_id
"""

_PKS_SQL = """
SELECT cols.column_name
FROM ALL_CONSTRAINTS cons
JOIN ALL_CONS_COLUMNS cols
  ON cons.constraint_name = cols.constraint_name AND cons.owner = cols.owner
WHERE cons.owner = :owner AND cons.table_name = :t AND cons.constraint_type = 'P'
"""

_FKS_SQL = """
SELECT a.column_name AS source_column,
       c_pk.table_name AS target_table,
       b.column_name AS target_column
FROM ALL_CONS_COLUMNS a
JOIN ALL_CONSTRAINTS c
  ON a.constraint_name = c.constraint_name AND a.owner = c.owner
JOIN ALL_CONSTRAINTS c_pk
  ON c.r_constraint_name = c_pk.constraint_name AND c.r_owner = c_pk.owner
JOIN ALL_CONS_COLUMNS b
  ON c_pk.constraint_name = b.constraint_name AND c_pk.owner = b.owner
  AND a.position = b.position
WHERE c.owner = :owner AND c.table_name = :t AND c.constraint_type = 'R'
"""

_ROW_COUNT_SQL = """
SELECT num_rows AS estimate FROM ALL_TABLES WHERE owner = :owner AND table_name = :t
"""


def main() -> int:
    args = _parse_args()
    if not (args.host and args.service and args.user and args.password):
        logger.error("Missing connection params (host/service/user/password). See --help.")
        return 1
    owner = (args.owner or args.user).upper()
    tables = _load_table_list(args)
    if not tables:
        logger.error("No tables given. Use --tables or --tables-file.")
        return 1

    # Import ARIA modules (repo root must be on PYTHONPATH).
    try:
        from backend.app.db.executor import get_executor
        from backend.app.db.models import DatabaseType, DBConfig
        from backend.app.services.vault_enum_sampler import _is_varchar, _quote_ident
    except Exception as e:  # noqa: BLE001
        logger.error("Cannot import ARIA modules — run with PYTHONPATH=<repo root>. (%s)", e)
        return 1

    config = DBConfig(
        db_type=DatabaseType.ORACLE,
        host=args.host,
        port=args.port,
        database=args.service,
        username=args.user,
        password=args.password,
    )
    try:
        executor = get_executor(config)
        executor.execute("SELECT 1 FROM dual", {})
    except Exception as e:  # noqa: BLE001
        logger.error("Connection failed: %s", e)
        return 1

    out_tables: list[dict] = []
    errors: list[dict] = []

    def _run(sql: str, params: dict) -> list[dict]:
        return executor.execute(sql, params)

    for t in tables:
        logger.info("extracting %s.%s", owner, t)
        entry: dict = {
            "table_name": t,
            "description": None,
            "row_count": None,
            "columns": [],
            "relationships": [],
            "enum_values": {},
        }
        if not args.no_sample_data:
            entry["sample_rows"] = []

        # columns
        try:
            cols = _run(_COLUMNS_SQL, {"owner": owner, "t": t})
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "columns", "error": str(e)})
            out_tables.append(entry)
            continue
        if not cols:
            errors.append({"table": t, "stage": "columns", "error": "no columns (table not found?)"})
            out_tables.append(entry)
            continue

        # pks
        pk_set: set[str] = set()
        try:
            for r in _run(_PKS_SQL, {"owner": owner, "t": t}):
                pk_set.add(str(next(iter(r.values()))))
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "pks", "error": str(e)})

        col_dicts = []
        for c in cols:
            name = c.get("COLUMN_NAME") or c.get("column_name")
            dtype = c.get("DATA_TYPE") or c.get("data_type")
            nullable = (c.get("IS_NULLABLE") or c.get("is_nullable")) == "YES"
            col_dicts.append({
                "name": name,
                "data_type": dtype,
                "nullable": nullable,
                "is_pk": name in pk_set,
                "description": None,
                "example_values": [],
            })
        entry["columns"] = col_dicts

        # row count
        try:
            rc = _run(_ROW_COUNT_SQL, {"owner": owner, "t": t})
            if rc:
                val = next(iter(rc[0].values()))
                entry["row_count"] = int(val) if val is not None else None
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "row_count", "error": str(e)})

        # fks
        try:
            for r in _run(_FKS_SQL, {"owner": owner, "t": t}):
                entry["relationships"].append({
                    "source_column": r.get("SOURCE_COLUMN") or r.get("source_column"),
                    "target_table": r.get("TARGET_TABLE") or r.get("target_table"),
                    "target_column": r.get("TARGET_COLUMN") or r.get("target_column"),
                    "relationship_type": "foreign_key",
                })
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "fks", "error": str(e)})

        # enum values (2-query pattern mirrored from vault_enum_sampler)
        qt = f'"{owner}".{_quote_ident(t)}'
        for c in col_dicts:
            if not _is_varchar(c["data_type"]):
                continue
            col = c["name"]
            try:
                cnt = _run(
                    f"SELECT COUNT(DISTINCT {_quote_ident(col)}) AS c FROM {qt}", {}
                )
                n = next(iter(cnt[0].values())) if cnt else None
                if n is None or int(n) == 0 or int(n) > args.max_cardinality:
                    continue
                drows = _run(
                    f"SELECT DISTINCT {_quote_ident(col)} AS v FROM {qt} "
                    f"WHERE {_quote_ident(col)} IS NOT NULL "
                    f"FETCH FIRST {args.max_cardinality} ROWS ONLY",
                    {},
                )
                vals = sorted({
                    str(next(iter(r.values()))).strip()
                    for r in drows if r and next(iter(r.values()), None) is not None
                })
                if vals:
                    entry["enum_values"][col] = vals
                    c["example_values"] = vals[:10]
            except Exception as e:  # noqa: BLE001
                errors.append({"table": t, "stage": "enum", "column": col, "error": str(e)})

        # sample rows
        if not args.no_sample_data:
            try:
                srows = _run(f"SELECT * FROM {qt} FETCH FIRST {args.sample_rows} ROWS ONLY", {})
                entry["sample_rows"] = [
                    {k: (str(v) if v is not None else None) for k, v in r.items()}
                    for r in srows
                ]
            except Exception as e:  # noqa: BLE001
                errors.append({"table": t, "stage": "sample_rows", "error": str(e)})

        out_tables.append(entry)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "owner": owner,
        "source": "extract-db-metadata.py",
        "tables": out_tables,
        "errors": errors,
    }

    out_path = args.out or f"db-metadata-{owner.lower()}-{datetime.now(UTC):%Y%m%d-%H%M}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(
        "wrote %s — %d tables, %d errors%s",
        out_path, len(out_tables), len(errors),
        " (PII: contains sample rows)" if not args.no_sample_data else "",
    )
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
