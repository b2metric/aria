#!/usr/bin/env python3
"""vault-extract-remote.py — full offline Oracle snapshot for a vault rebuild.

Run this on a machine that can reach the *remote* customer Oracle DB (e.g. the
stc-kuwait DWH host). It captures EVERYTHING that shapes the vault for the tables
you name and writes it to disk (JSON + optional Parquet). You then copy those
artifacts to a box with ARIA reach and run ``scripts/vault-replace-from-metadata.py``
to rebuild the vault (dtypes / enums / relationships refreshed) while preserving
curated descriptions + Example Queries.

This is a SUPERSET of ``scripts/vault-extract-standalone.py``: in addition to
columns / enums / FKs / row-count it also captures **materialized-view & view
query definitions** and **sample rows**, and can emit **Parquet** alongside JSON.
Because it captures sample rows (potential PII), the artifacts are NOT PII-safe —
keep them internal. (The JSON is still import-compatible with
``/api/workspaces/vault/import-metadata``: the extra keys are ignored there.)

Dependencies:
  - REQUIRED: ``oracledb`` (pure-Python thin driver — no Instant Client needed).
  - OPTIONAL: ``pyarrow`` (only for --parquet). Stage both on an air-gapped box:
        # on an internet machine:
        pip download oracledb pyarrow -d ./wheels --only-binary=:all:
        # copy ./wheels over, then on the air-gapped box:
        pip install --no-index --find-links ./wheels oracledb pyarrow

Usage:
    python scripts/vault-extract-remote.py \
        --host MIS-DWH.STC.COM.KW --port 1521 --service stcdw \
        --user COMMBI_PROD --password '***' --owner COMMBI_PROD \
        --tables-file active_tables.txt \
        --out-dir ./stc-vault-snapshot --sample-rows 20

Every connection flag falls back to an env var (ORA_HOST / ORA_PORT /
ORA_SERVICE / ORA_USER / ORA_PASSWORD / ORA_OWNER) so the password need not
appear in argv.

Exit codes: 0 = all tables ok; 1 = config/connection error; 2 = partial (some
tables/objects failed; artifacts still written with an ``errors`` array).
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import decimal
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("vault-extract-remote")

SCHEMA_VERSION = "1.0"
# Mirrors backend/app/services/vault_enum_sampler._VARCHAR_PREFIXES so offline
# enum sampling matches what the live vault sync would produce.
_VARCHAR_PREFIXES = ("VARCHAR", "CHAR", "NVARCHAR", "NCHAR", "TEXT", "STRING")


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)  # noqa: UP017 — 3.8+ portable for air-gapped boxes


def _is_varchar(dtype: str | None) -> bool:
    t = (dtype or "").upper()
    return any(t.startswith(p) for p in _VARCHAR_PREFIXES)


def _quote_ident(name: str) -> str:
    # Quote defensively in case of reserved-word identifiers.
    return '"' + name.replace('"', '""') + '"'


def _coerce(value: Any) -> Any:
    """Coerce an Oracle cell value to a JSON/Parquet-safe scalar.

    Dates/timestamps → ISO string, Decimal → float (int when integral),
    bytes → base64 string, everything else passed through. None stays None.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")
    return str(value)


# ── Oracle catalog SQL (ALL_* with an owner filter; owner may differ from user) ──
_COLUMNS_SQL = """
SELECT column_name, data_type,
       CASE WHEN nullable = 'Y' THEN 'YES' ELSE 'NO' END AS is_nullable,
       num_distinct
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
       b.column_name AS target_column,
       c.constraint_name AS constraint_name
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
_MVIEW_SQL = "SELECT query FROM ALL_MVIEWS WHERE owner = :owner AND mview_name = :t"
_VIEW_SQL = "SELECT text FROM ALL_VIEWS WHERE owner = :owner AND view_name = :t"
_DEPENDENTS_SQL = """
SELECT DISTINCT name, type
FROM ALL_DEPENDENCIES
WHERE referenced_owner = :owner AND referenced_name = :t
  AND type IN ('VIEW', 'MATERIALIZED VIEW')
"""


class OracleCatalog:
    """Thin cursor-backed reader for the Oracle data dictionary.

    All DB access is funneled through this class so the extraction/assembly
    logic (``build_table_entry`` etc.) can be unit-tested against a fake.
    """

    def __init__(self, cursor: Any, parallel: int | None = None, sample_pct: float | None = None) -> None:
        self._cur = cursor
        self._hint = f"/*+ PARALLEL({int(parallel)}) */ " if parallel else ""
        self._sample_pct = sample_pct

    def _rows(self, sql: str, params: dict) -> list[dict]:
        self._cur.execute(sql, params)
        cols = [d[0].upper() for d in self._cur.description]
        return [dict(zip(cols, row)) for row in self._cur.fetchall()]  # noqa: B905 (3.8+)

    def columns(self, owner: str, t: str) -> list[dict]:
        return self._rows(_COLUMNS_SQL, {"owner": owner, "t": t})

    def pks(self, owner: str, t: str) -> set[str]:
        return {str(r["COLUMN_NAME"]) for r in self._rows(_PKS_SQL, {"owner": owner, "t": t})}

    def fks(self, owner: str, t: str) -> list[dict]:
        return self._rows(_FKS_SQL, {"owner": owner, "t": t})

    def row_count(self, owner: str, t: str) -> int | None:
        rows = self._rows(_ROW_COUNT_SQL, {"owner": owner, "t": t})
        if rows and rows[0].get("NUM_ROWS") is not None:
            return int(rows[0]["NUM_ROWS"])
        return None

    def distinct_count(self, owner: str, t: str, col: str) -> int | None:
        qt = f'"{owner}".{_quote_ident(t)}'
        self._cur.execute(f"SELECT {self._hint}COUNT(DISTINCT {_quote_ident(col)}) FROM {qt}")
        n = self._cur.fetchone()[0]
        return None if n is None else int(n)

    def distinct_values(self, owner: str, t: str, col: str, limit: int) -> list[str]:
        qt = f'"{owner}".{_quote_ident(t)}'
        qc = _quote_ident(col)
        # SAMPLE(pct) reads only a fraction of blocks — bounds cost on huge tables
        # (an enum column's small value set is very likely still fully captured).
        sample = f" SAMPLE ({self._sample_pct})" if self._sample_pct else ""
        self._cur.execute(
            f"SELECT {self._hint}DISTINCT {qc} FROM {qt}{sample} WHERE {qc} IS NOT NULL "
            f"FETCH FIRST {int(limit)} ROWS ONLY"
        )
        return sorted(
            {str(r[0]).strip() for r in self._cur.fetchall() if r[0] is not None}
        )

    def sample_rows(self, owner: str, t: str, limit: int) -> list[dict]:
        qt = f'"{owner}".{_quote_ident(t)}'
        self._cur.execute(f"SELECT {self._hint}* FROM {qt} FETCH FIRST {int(limit)} ROWS ONLY")
        names = [d[0] for d in self._cur.description]
        out: list[dict] = []
        for row in self._cur.fetchall():
            out.append({names[i]: _coerce(v) for i, v in enumerate(row)})
        return out

    def self_view_query(self, owner: str, t: str) -> dict | None:
        """If ``t`` is itself a materialized view or view, return its definition."""
        mv = self._rows(_MVIEW_SQL, {"owner": owner, "t": t})
        if mv and mv[0].get("QUERY") is not None:
            return {"name": t, "kind": "materialized view", "query": str(mv[0]["QUERY"]).strip()}
        vw = self._rows(_VIEW_SQL, {"owner": owner, "t": t})
        if vw and vw[0].get("TEXT") is not None:
            return {"name": t, "kind": "view", "query": str(vw[0]["TEXT"]).strip()}
        return None

    def dependents(self, owner: str, t: str) -> list[dict]:
        return self._rows(_DEPENDENTS_SQL, {"owner": owner, "t": t})


def build_table_entry(
    catalog: OracleCatalog,
    owner: str,
    table: str,
    *,
    max_cardinality: int = 50,
    sample_limit: int = 20,
    skip_enums: bool = False,
) -> tuple[dict, list[dict]]:
    """Assemble one table's metadata entry (+ a per-table errors list).

    Pure orchestration over the ``catalog`` interface so it is unit-testable.
    ``description`` and per-column ``description`` are intentionally left None —
    the replacer preserves the curated ones from the existing vault.
    """
    errors: list[dict] = []
    entry: dict = {
        "table_name": table,
        "description": None,
        "row_count": None,
        "columns": [],
        "relationships": [],
        "enum_values": {},
        "materialized_view": None,
        "sample_rows": [],
    }

    cols = catalog.columns(owner, table)
    if not cols:
        errors.append({"table": table, "stage": "columns", "error": "no columns (not found?)"})
        return entry, errors

    try:
        pk_set = catalog.pks(owner, table)
    except Exception as e:  # noqa: BLE001
        pk_set = set()
        errors.append({"table": table, "stage": "pks", "error": str(e)})

    col_dicts = [
        {
            "name": c["COLUMN_NAME"],
            "data_type": c["DATA_TYPE"],
            "nullable": c["IS_NULLABLE"] == "YES",
            "is_pk": c["COLUMN_NAME"] in pk_set,
            "description": None,
            "example_values": [],
        }
        for c in cols
    ]
    entry["columns"] = col_dicts
    # Optimizer-stats cardinality per column (ALL_TAB_COLUMNS.NUM_DISTINCT) — lets
    # us skip high-cardinality columns WITHOUT a COUNT(DISTINCT) full-table scan.
    nd_map = {c["COLUMN_NAME"]: c.get("NUM_DISTINCT") for c in cols}

    try:
        entry["row_count"] = catalog.row_count(owner, table)
    except Exception as e:  # noqa: BLE001
        errors.append({"table": table, "stage": "row_count", "error": str(e)})

    try:
        for r in catalog.fks(owner, table):
            entry["relationships"].append(
                {
                    "source_column": r["SOURCE_COLUMN"],
                    "target_table": r["TARGET_TABLE"],
                    "target_column": r["TARGET_COLUMN"],
                    "relationship_type": "foreign_key",
                    "constraint_name": r.get("CONSTRAINT_NAME"),
                }
            )
    except Exception as e:  # noqa: BLE001
        errors.append({"table": table, "stage": "fks", "error": str(e)})

    # Low-cardinality enum sampling (the "Bundles not Bundle" fix).
    if not skip_enums:
        for c in col_dicts:
            if not _is_varchar(c["data_type"]):
                continue
            col = c["name"]
            try:
                approx = nd_map.get(col)
                if approx is not None:
                    # cardinality from optimizer stats → no scan needed to gate
                    if approx == 0 or approx > max_cardinality:
                        continue
                else:
                    # stats missing → fall back to a COUNT(DISTINCT) scan
                    n = catalog.distinct_count(owner, table, col)
                    if n is None or n == 0 or n > max_cardinality:
                        continue
                vals = catalog.distinct_values(owner, table, col, max_cardinality)
                if vals:
                    entry["enum_values"][col] = vals
                    c["example_values"] = vals[:10]
            except Exception as e:  # noqa: BLE001
                errors.append({"table": table, "stage": "enum", "column": col, "error": str(e)})

    # Materialized-view / view definition when the object itself is a view/MV.
    try:
        mv = catalog.self_view_query(owner, table)
        if mv:
            entry["materialized_view"] = mv
    except Exception as e:  # noqa: BLE001
        errors.append({"table": table, "stage": "mview", "error": str(e)})

    # Sample rows (PII — artifact only, never written into the vault).
    if sample_limit > 0:
        try:
            entry["sample_rows"] = catalog.sample_rows(owner, table, sample_limit)
        except Exception as e:  # noqa: BLE001
            errors.append({"table": table, "stage": "sample", "error": str(e)})

    return entry, errors


def collect_related_views(
    catalog: OracleCatalog, owner: str, tables: list[str]
) -> tuple[list[dict], list[dict]]:
    """Find views / materialized views that DEPEND ON any of ``tables`` and pull
    their SQL definitions. Deduplicated by object name; a view referencing several
    of the tables lists them all under ``references``."""
    errors: list[dict] = []
    seen: dict[str, dict] = {}
    for t in tables:
        try:
            deps = catalog.dependents(owner, t)
        except Exception as e:  # noqa: BLE001
            errors.append({"table": t, "stage": "dependents", "error": str(e)})
            continue
        for d in deps:
            name = str(d.get("NAME"))
            if not name or name in tables:
                continue
            if name not in seen:
                try:
                    view = catalog.self_view_query(owner, name)
                except Exception as e:  # noqa: BLE001
                    errors.append({"view": name, "stage": "view_def", "error": str(e)})
                    view = None
                seen[name] = view or {
                    "name": name,
                    "kind": str(d.get("TYPE", "")).lower(),
                    "query": None,
                }
                seen[name]["references"] = []
            if t not in seen[name]["references"]:
                seen[name]["references"].append(t)
    return list(seen.values()), errors


def assemble_payload(
    owner: str, tables: list[dict], related_views: list[dict], errors: list[dict]
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "db_type": "oracle",  # read by enrich_from_metadata_json to create vault tables
        "generated_at": _utcnow().isoformat(),
        "owner": owner,
        "source": "vault-extract-remote.py",
        "tables": tables,
        "related_views": related_views,
        "errors": errors,
    }


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_parquet(payload: dict, out_dir: Path) -> list[str]:
    """Write per-table sample rows to Parquet. No-op (returns []) if pyarrow is
    unavailable or there are no sample rows."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        logger.warning("pyarrow not installed — skipping Parquet (pip install pyarrow).")
        return []

    pdir = out_dir / "parquet"
    pdir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for tbl in payload.get("tables", []):
        rows = tbl.get("sample_rows") or []
        if not rows:
            continue
        name = tbl["table_name"]
        try:
            table = pa.Table.from_pylist(rows)
        except (pa.lib.ArrowInvalid, pa.lib.ArrowTypeError):
            # Mixed/unstable column types → stringify every cell and retry.
            safe = [{k: (None if v is None else str(v)) for k, v in r.items()} for r in rows]
            table = pa.Table.from_pylist(safe)
        fp = pdir / f"{name}.parquet"
        pq.write_table(table, fp)
        written.append(str(fp))
    return written


def _load_table_list(args: argparse.Namespace) -> list[str]:
    names: list[str] = []
    if args.tables:
        names += [t.strip() for t in args.tables.split(",") if t.strip()]
    if args.tables_file:
        raw = Path(args.tables_file).read_text(encoding="utf-8")
        for line in raw.splitlines():
            if line.lstrip().startswith("#"):  # comment line
                continue
            names += [t.strip() for t in line.split(",") if t.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        u = n.upper()
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Full offline Oracle snapshot for a vault rebuild.")
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
    p.add_argument("--skip-enums", action="store_true",
                   help="Skip enum sampling entirely (fastest; no DISTINCT queries)")
    p.add_argument("--parallel", type=int, default=None,
                   help="Add an Oracle /*+ PARALLEL(N) */ hint to enum/sample scans")
    p.add_argument("--enum-sample-pct", type=float, default=None,
                   help="Use SAMPLE(pct) for the DISTINCT-value fetch (bounds cost on huge tables)")
    p.add_argument("--sample-rows", type=int, default=20,
                   help="Sample rows per table (0 disables; PII — artifact only)")
    p.add_argument("--no-related-views", action="store_true",
                   help="Skip the scan for views/MVs that depend on the tables")
    p.add_argument("--thick", action="store_true",
                   help="Use oracledb thick mode (Oracle Instant Client). Needed for "
                        "old 10G password verifiers → DPY-3015 in thin mode.")
    p.add_argument("--lib-dir", default=os.environ.get("ORA_LIB_DIR"),
                   help="Instant Client dir for --thick (else oracledb's default search)")
    p.add_argument("--parquet", dest="parquet", action="store_true", default=True,
                   help="Also write per-table sample-row Parquet (default on)")
    p.add_argument("--no-parquet", dest="parquet", action="store_false")
    p.add_argument("--out-dir", default=".", help="Output directory for artifacts")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not (args.host and args.service and args.user and args.password):
        logger.error("Missing connection params (host/service/user/password). See --help.")
        return 1

    try:
        import oracledb
    except ImportError:
        logger.error(
            "oracledb is required. Air-gapped box: `pip download oracledb -d ./wheels "
            "--only-binary=:all:` on an internet machine, copy over, then "
            "`pip install --no-index --find-links ./wheels oracledb`."
        )
        return 1

    # Thick mode (Oracle Instant Client) is required for legacy 10G password
    # verifiers — thin mode raises DPY-3015 "password verifier type ... not supported".
    if args.thick:
        try:
            oracledb.init_oracle_client(lib_dir=args.lib_dir or None)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "Thick mode init failed: %s\nInstall Oracle Instant Client and pass "
                "--lib-dir /path/to/instantclient (or set ORA_LIB_DIR). macOS ARM: "
                "download the ARM64 Instant Client Basic, unzip, then "
                "`xattr -r -d com.apple.quarantine <dir>`.",
                e,
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

    cur = conn.cursor()
    catalog = OracleCatalog(cur, parallel=args.parallel, sample_pct=args.enum_sample_pct)
    out_tables: list[dict] = []
    all_errors: list[dict] = []

    for t in tables:
        logger.info("extracting %s.%s", owner, t)
        entry, errs = build_table_entry(
            catalog, owner, t,
            max_cardinality=args.max_cardinality, sample_limit=args.sample_rows,
            skip_enums=args.skip_enums,
        )
        out_tables.append(entry)
        all_errors.extend(errs)

    related_views: list[dict] = []
    if not args.no_related_views:
        logger.info("scanning for dependent views / materialized views")
        related_views, view_errs = collect_related_views(catalog, owner, tables)
        all_errors.extend(view_errs)

    cur.close()
    conn.close()

    payload = assemble_payload(owner, out_tables, related_views, all_errors)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{_utcnow():%Y%m%d-%H%M}"
    json_path = out_dir / f"db-metadata-{owner.lower()}-{stamp}.json"
    write_json(payload, json_path)

    parquet_files: list[str] = []
    if args.parquet:
        parquet_files = write_parquet(payload, out_dir)

    manifest = {
        "generated_at": payload["generated_at"],
        "owner": owner,
        "tables": [t["table_name"] for t in out_tables],
        "table_count": len(out_tables),
        "related_view_count": len(related_views),
        "sample_rows_per_table": args.sample_rows,
        "json_file": json_path.name,
        "parquet_files": [Path(p).name for p in parquet_files],
        "error_count": len(all_errors),
        "pii_warning": bool(args.sample_rows > 0),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(
        "wrote %s (%d tables, %d related views, %d parquet, %d errors)%s",
        json_path, len(out_tables), len(related_views), len(parquet_files), len(all_errors),
        " — contains sample rows (PII), keep internal" if args.sample_rows > 0 else "",
    )
    logger.info(
        "next: copy %s to an ARIA-reachable box and run "
        "`python scripts/vault-replace-from-metadata.py --workspace stc-kuwait --json %s`",
        out_dir, json_path.name,
    )
    return 2 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
