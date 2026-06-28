#!/usr/bin/env python3
"""vault-extract-standalone.py — self-contained offline Oracle metadata extractor.

Unlike ``scripts/extract-db-metadata.py`` (which imports the whole ARIA backend
+ its venv), this script is **standalone**: its ONLY third-party dependency is
``oracledb`` (the pure-Python thin driver — no Oracle Instant Client needed).
Everything else is the Python standard library. That makes it runnable on an
air-gapped / no-internet customer box where you cannot install the ARIA stack.

What it does, for ONLY the tables you name:
  - column metadata (name, data_type, nullable, is_pk)
  - low-cardinality enum DISTINCT values (the "Bundles not Bundle" fix)
  - row count (ALL_TABLES.NUM_ROWS estimate)
  - foreign-key relationships

…and writes ONE JSON file (PII-safe: NO sample rows). Copy that JSON to a machine
with ARIA reach and upload it with ``scripts/vault-upload.py`` (or POST it to
``/api/workspaces/vault/import-metadata``). The vault tables are CREATED from the
JSON columns and then enriched + enum-injected — no live schema discovery needed.

Getting oracledb onto an air-gapped box (it is pure-Python, single wheel):
    # on an internet box:
    pip download oracledb -d ./wheels --only-binary=:all:
    # copy ./wheels to the air-gapped box, then:
    pip install --no-index --find-links ./wheels oracledb

Usage:
    python scripts/vault-extract-standalone.py \
        --host MIS-DWH.STC.COM.KW --port 1521 --service stcdw \
        --user COMMBI_PROD --password '***' --owner COMMBI_PROD \
        --tables FCT_PREP_RECHARGE,FCT_PREP_PROVISION \
        --out db-metadata-stc.json

    # or a file with one table per line / comma-separated:
    python scripts/vault-extract-standalone.py ... --tables-file active_tables.txt

Secrets: every flag falls back to an env var (ORA_HOST/ORA_PORT/ORA_SERVICE/
ORA_USER/ORA_PASSWORD/ORA_OWNER) so the password need not appear in argv.

Exit codes: 0 = all tables ok; 1 = config/connection error; 2 = partial (some
tables failed; file still written with an ``errors`` array).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("vault-extract-standalone")

SCHEMA_VERSION = "1.0"
# Mirrors backend/app/services/vault_enum_sampler._VARCHAR_PREFIXES so the offline
# enum sampling matches what the live vault sync would produce.
_VARCHAR_PREFIXES = ("VARCHAR", "CHAR", "NVARCHAR", "NCHAR", "TEXT", "STRING")


def _is_varchar(dtype: str | None) -> bool:
    t = (dtype or "").upper()
    return any(t.startswith(p) for p in _VARCHAR_PREFIXES)


def _quote_ident(name: str) -> str:
    # Quote defensively in case of reserved-word column names.
    return '"' + name.replace('"', '""') + '"'


# ── Oracle catalog SQL (ALL_* with an owner filter; owner may differ from user) ──
_COLUMNS_SQL = """
SELECT column_name, data_type,
       CASE WHEN nullable = 'Y' THEN 'YES' ELSE 'NO' END AS is_nullable
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

_ROW_COUNT_SQL = "SELECT num_rows FROM ALL_TABLES WHERE owner = :owner AND table_name = :t"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standalone offline Oracle metadata extractor.")
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
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        u = n.upper()
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _rows(cur, sql: str, params: dict) -> list[dict]:
    """Execute and return rows as list[dict] keyed by UPPERCASE column name."""
    cur.execute(sql, params)
    cols = [d[0].upper() for d in cur.description]
    # zip(strict=) is 3.10+; keep portable for old air-gapped Pythons (3.8+).
    return [dict(zip(cols, row)) for row in cur.fetchall()]  # noqa: B905


def main() -> int:
    args = _parse_args()
    if not (args.host and args.service and args.user and args.password):
        logger.error("Missing connection params (host/service/user/password). See --help.")
        return 1

    try:
        import oracledb
    except ImportError:
        logger.error(
            "oracledb is required. On an air-gapped box, pre-stage the wheel: "
            "`pip download oracledb -d ./wheels --only-binary=:all:` on an internet "
            "machine, copy it over, then `pip install --no-index --find-links ./wheels oracledb`."
        )
        return 1

    owner = (args.owner or args.user).upper()
    tables = _load_table_list(args)
    if not tables:
        logger.error("No tables given. Use --tables or --tables-file.")
        return 1

    dsn = f"{args.host}:{args.port}/{args.service}"
    try:
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
    except Exception as e:  # noqa: BLE001
        logger.error("Connection failed (%s): %s", dsn, e)
        return 1

    out_tables: list[dict] = []
    errors: list[dict] = []
    cur = conn.cursor()

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

        try:
            cols = _rows(cur, _COLUMNS_SQL, {"owner": owner, "t": t})
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "columns", "error": str(e)})
            out_tables.append(entry)
            continue
        if not cols:
            errors.append({"table": t, "stage": "columns", "error": "no columns (table not found?)"})
            out_tables.append(entry)
            continue

        pk_set: set[str] = set()
        try:
            for r in _rows(cur, _PKS_SQL, {"owner": owner, "t": t}):
                pk_set.add(str(r["COLUMN_NAME"]))
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "pks", "error": str(e)})

        col_dicts = []
        for c in cols:
            name = c["COLUMN_NAME"]
            col_dicts.append({
                "name": name,
                "data_type": c["DATA_TYPE"],
                "nullable": c["IS_NULLABLE"] == "YES",
                "is_pk": name in pk_set,
                "description": None,
                "example_values": [],
            })
        entry["columns"] = col_dicts

        try:
            rc = _rows(cur, _ROW_COUNT_SQL, {"owner": owner, "t": t})
            if rc and rc[0]["NUM_ROWS"] is not None:
                entry["row_count"] = int(rc[0]["NUM_ROWS"])
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "row_count", "error": str(e)})

        try:
            for r in _rows(cur, _FKS_SQL, {"owner": owner, "t": t}):
                entry["relationships"].append({
                    "source_column": r["SOURCE_COLUMN"],
                    "target_table": r["TARGET_TABLE"],
                    "target_column": r["TARGET_COLUMN"],
                    "relationship_type": "foreign_key",
                })
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "fks", "error": str(e)})

        # enum values — 2-query pattern mirrored from vault_enum_sampler
        qt = f'"{owner}".{_quote_ident(t)}'
        for c in col_dicts:
            if not _is_varchar(c["data_type"]):
                continue
            col = c["name"]
            qcol = _quote_ident(col)
            try:
                cur.execute(f"SELECT COUNT(DISTINCT {qcol}) FROM {qt}")
                n = cur.fetchone()[0]
                if n is None or int(n) == 0 or int(n) > args.max_cardinality:
                    continue
                cur.execute(
                    f"SELECT DISTINCT {qcol} FROM {qt} WHERE {qcol} IS NOT NULL "
                    f"FETCH FIRST {args.max_cardinality} ROWS ONLY"
                )
                vals = sorted({
                    str(row[0]).strip() for row in cur.fetchall() if row[0] is not None
                })
                if vals:
                    entry["enum_values"][col] = vals
                    c["example_values"] = vals[:10]
            except Exception as e:  # noqa: BLE001
                errors.append({"table": t, "stage": "enum", "column": col, "error": str(e)})

        out_tables.append(entry)

    cur.close()
    conn.close()

    payload = {
        "schema_version": SCHEMA_VERSION,
        "db_type": "oracle",  # read by enrich_from_metadata_json to create the vault tables
        "generated_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 (3.8+ portable)
        "owner": owner,
        "source": "vault-extract-standalone.py",
        "tables": out_tables,
        "errors": errors,
    }

    out_path = args.out or f"db-metadata-{owner.lower()}-{datetime.now(timezone.utc):%Y%m%d-%H%M}.json"  # noqa: UP017
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("wrote %s — %d tables, %d errors (PII-safe: no sample rows)",
                out_path, len(out_tables), len(errors))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
