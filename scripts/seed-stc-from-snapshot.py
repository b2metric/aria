#!/usr/bin/env python3
"""seed-stc-from-snapshot.py — rebuild the local mock Oracle demo DB from a snapshot.

Derives the demo dataset FROM the real sample data captured in the extraction
snapshot (vault-extract-remote.py output), instead of hard-coded fake values.

For each of the 9 tables it:
  - DROP + CREATE from the snapshot's real columns/dtypes (VARCHAR2(4000) for text,
    NUMBER, DATE — permissive; the snapshot doesn't carry lengths),
  - learns a value pool per column = observed sample values ∪ enum values,
  - generates N rows drawing every column from its real pool, while keeping
    cross-table JOIN consistency via a SHARED subscriber pool (CONTRNO/SUBNO +
    denormalised demographics like NATIONALITY/REGION/CONTRACT_CATEGORY) and a
    shared product pool (real DIM_PREP_PRODUCTS rows / OFFER_IDs),
  - spreads DATE columns across the last ~12 months so time-series demos work.

Deterministic (seed=42). Connects thin-mode to the local mock (localhost:1521).

    uv run python scripts/seed-stc-from-snapshot.py \
        --json vault-rebuild-bundle/scripts/stc-vault-snapshot/db-metadata-*.json \
        [--scale 1.0]
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import random
import sys
from pathlib import Path

import oracledb

SEED = 42
REF_DATE = dt.datetime(2026, 6, 8)
WINDOW_DAYS = 365

# Columns that identify/travel with a subscriber — kept consistent across every
# table a subscriber appears in (so SUBNO/CONTRNO joins line up and a subscriber's
# nationality/region/category never contradict between tables).
_SUBSCRIBER_COLS = [
    "CONTRNO", "SUBNO", "NATIONALITY", "NATIONALITY_GROUP", "REGION",
    "CONTRACT_CATEGORY", "PREPOST_PAID", "PREPOST_PAID_DESC",
]
# Product-dimension columns (travel with a chosen DIM_PREP_PRODUCTS row).
_PRODUCT_COLS = [
    "OFFER_ID", "PROD_OFFERING_ID", "BUSINESS", "PRODUCT_OFFER_NAME",
    "PRODUCT_TYPE", "SUB_PRODUCT_TYPE", "PRODUCT_PRICE", "EQUIPID",
    "PRODUCT_VALIDITY", "PRODUCT_BENEFITS",
]

# Per-table row targets (before --scale). dim tables are sized to their pools.
_ROW_TARGETS = {
    "FCT_PREP_REV": 6000,
    "FCT_PREP_MASTER": 400,
    "FCT_PREP_MASTER_HIST": 2400,
    "FCT_PREP_PROVISION": 3000,
    "FCT_PREP_RECHARGE": 4000,
    "FCT_PREP_ROAMING": 2000,
    "FCT_PREP_USAGE": 5000,
    "DIM_PREP_STATE_SCD2": 400,
    "DIM_PREP_PRODUCTS": 0,  # seeded directly from the real sample rows
}
N_SUBSCRIBERS = 400


def ddl_type(dtype: str) -> str:
    t = (dtype or "").upper()
    if t == "NUMBER":
        return "NUMBER"
    if t == "DATE" or t.startswith("TIMESTAMP"):
        return "DATE"
    return "VARCHAR2(4000)"  # VARCHAR2/CHAR/RAW/NVARCHAR/... — permissive for a demo


def _col_pool(table: dict, col: str) -> list:
    """Observed non-null sample values ∪ enum values for a column."""
    vals: list = []
    seen = set()
    for r in table.get("sample_rows", []):
        v = r.get(col)
        if v is not None and str(v) not in seen:
            seen.add(str(v))
            vals.append(v)
    for v in table.get("enum_values", {}).get(col, []):
        if str(v) not in seen:
            seen.add(str(v))
            vals.append(v)
    return vals


def _coerce(value, target: str, rng: random.Random):
    """Coerce a pool value to the target Oracle column type."""
    t = (target or "").upper()
    if value is None:
        return None
    if t == "NUMBER":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if t == "DATE" or t.startswith("TIMESTAMP"):
        # parse ISO sample dates; otherwise spread across the window
        s = str(value)
        try:
            return dt.datetime.fromisoformat(s)
        except ValueError:
            return REF_DATE - dt.timedelta(days=rng.randint(0, WINDOW_DAYS))
    return str(value)


def _rand_date(rng: random.Random) -> dt.datetime:
    return REF_DATE - dt.timedelta(
        days=rng.randint(0, WINDOW_DAYS), seconds=rng.randint(0, 86399)
    )


def build_subscribers(master: dict, rng: random.Random, n: int) -> list[dict]:
    """Synthesize a shared subscriber pool from the master table's real sample
    distributions (new CONTRNO/SUBNO in the observed shape + real demographics)."""
    pools = {c: _col_pool(master, c) for c in _SUBSCRIBER_COLS}
    subs: list[dict] = []
    for _ in range(n):
        s: dict = {}
        s["CONTRNO"] = str(rng.choice([1, 2, 7]) * 10**9 + rng.randint(0, 999_999_999))
        s["SUBNO"] = "5" + str(rng.randint(0, 9_999_999)).zfill(7)
        for c in _SUBSCRIBER_COLS:
            if c in ("CONTRNO", "SUBNO"):
                continue
            pool = pools.get(c) or []
            if pool:
                s[c] = rng.choice(pool)
        subs.append(s)
    return subs


def gen_rows(table: dict, cols: list[str], types: dict[str, str], n: int,
             subs: list[dict], products: list[dict], rng: random.Random) -> list[dict]:
    pools = {c: _col_pool(table, c) for c in cols}
    date_cols = {c for c in cols if ddl_type(types[c]) == "DATE"}
    has_product = any(c in cols for c in _PRODUCT_COLS)
    rows: list[dict] = []
    for _ in range(n):
        s = rng.choice(subs)
        p = rng.choice(products) if (has_product and products) else {}
        row: dict = {}
        for c in cols:
            if c in s:
                row[c] = _coerce(s[c], types[c], rng)
            elif c in p and p.get(c) is not None:
                row[c] = _coerce(p[c], types[c], rng)
            elif c in date_cols:
                row[c] = _rand_date(rng)
            elif pools.get(c):
                row[c] = _coerce(rng.choice(pools[c]), types[c], rng)
            else:
                row[c] = None
        rows.append(row)
    return rows


def _list_objects(cur, kind: str) -> list[str]:
    view = "user_mviews" if "MATERIALIZED" in kind else "user_views"
    col = "mview_name" if "MATERIALIZED" in kind else "view_name"
    try:
        return [r[0] for r in cur.execute(f"SELECT {col} FROM {view}")]
    except oracledb.DatabaseError:
        return []


def _safe(cur, sql: str) -> None:
    try:
        cur.execute(sql)
    except oracledb.DatabaseError:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Seed the mock Oracle demo DB from a snapshot.")
    ap.add_argument("--json", required=True)
    ap.add_argument("--scale", type=float, default=1.0, help="row-count multiplier")
    ap.add_argument("--dsn", default="localhost:1521/FREEPDB1")
    ap.add_argument("--user", default="stc")
    ap.add_argument("--password", default="stc123")
    args = ap.parse_args(argv)

    matches = glob.glob(args.json)
    if not matches:
        print(f"no JSON match: {args.json}", file=sys.stderr)
        return 1
    payload = json.loads(Path(sorted(matches)[-1]).read_text(encoding="utf-8"))
    tables = {t["table_name"].upper(): t for t in payload["tables"]}

    rng = random.Random(SEED)
    conn = oracledb.connect(user=args.user, password=args.password, dsn=args.dsn)
    cur = conn.cursor()

    # DROP existing MVs (dependents) then tables, ignore ORA-00942/12003.
    for mv in _list_objects(cur, "MATERIALIZED VIEW"):
        _safe(cur, f'DROP MATERIALIZED VIEW "{mv}"')
    for name in tables:
        _safe(cur, f'DROP TABLE "{name}" CASCADE CONSTRAINTS')
    conn.commit()

    # CREATE from snapshot columns.
    col_order: dict[str, list[str]] = {}
    col_types: dict[str, dict[str, str]] = {}
    for name, t in tables.items():
        cols = [c["name"].upper() for c in t["columns"]]
        types = {c["name"].upper(): c["data_type"] for c in t["columns"]}
        col_order[name], col_types[name] = cols, types
        defs = ", ".join(f'"{c}" {ddl_type(types[c])}' for c in cols)
        cur.execute(f'CREATE TABLE "{name}" ({defs})')
    conn.commit()
    print("Created tables:", list(tables))

    # Shared pools.
    subs = build_subscribers(tables["FCT_PREP_MASTER"], rng, N_SUBSCRIBERS)
    products = list(tables["DIM_PREP_PRODUCTS"].get("sample_rows", []))

    def insert(name: str, rows: list[dict]) -> int:
        if not rows:
            return 0
        cols = col_order[name]
        binds = ", ".join(f":{i + 1}" for i in range(len(cols)))
        data = [[r.get(c) for c in cols] for r in rows]
        cur.executemany(
            f'INSERT INTO "{name}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) '
            f"VALUES ({binds})",
            data,
        )
        conn.commit()
        return len(data)

    counts: dict[str, int] = {}

    # DIM_PREP_PRODUCTS — seed the real sample rows verbatim (the product dimension).
    prod_rows = [
        {c: _coerce(r.get(c), col_types["DIM_PREP_PRODUCTS"][c], rng)
         for c in col_order["DIM_PREP_PRODUCTS"]}
        for r in products
    ]
    counts["DIM_PREP_PRODUCTS"] = insert("DIM_PREP_PRODUCTS", prod_rows)

    # DIM_PREP_STATE_SCD2 — one row per subscriber.
    scd = tables["DIM_PREP_STATE_SCD2"]
    counts["DIM_PREP_STATE_SCD2"] = insert(
        "DIM_PREP_STATE_SCD2",
        gen_rows(scd, col_order["DIM_PREP_STATE_SCD2"], col_types["DIM_PREP_STATE_SCD2"],
                 N_SUBSCRIBERS, subs, products, rng),
    )

    # Fact tables.
    for name in ("FCT_PREP_MASTER", "FCT_PREP_MASTER_HIST", "FCT_PREP_REV",
                 "FCT_PREP_PROVISION", "FCT_PREP_RECHARGE", "FCT_PREP_ROAMING",
                 "FCT_PREP_USAGE"):
        n = int(_ROW_TARGETS[name] * args.scale)
        counts[name] = insert(
            name, gen_rows(tables[name], col_order[name], col_types[name], n,
                           subs, products, rng)
        )

    print("Seeded rows:", counts)

    # Sanity: revenue must span multiple nationalities AND months (no fragile join).
    nats, months = cur.execute(
        "SELECT COUNT(DISTINCT NATIONALITY), COUNT(DISTINCT TRUNC(EXEC_DATE,'MM')) "
        "FROM fct_prep_rev"
    ).fetchone()
    print(f"Sanity: fct_prep_rev -> {nats} nationality(ies) x {months} month(s)")
    conn.close()
    if (nats or 0) < 2 or (months or 0) < 2:
        print("ERROR: revenue would collapse — seeding is broken.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
