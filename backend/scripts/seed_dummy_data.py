#!/usr/bin/env python3
"""Seed the STC mock Oracle DB with realistic dummy data.

Creates any vault-documented table that doesn't yet exist in Oracle, then fills
all of them with JOIN-consistent, multi-month, multi-nationality dummy data so the
ARIA analytics queries (revenue by region, daily active users, recharges, ...)
return rich, chart-friendly results.

Why: the Obsidian vault (docs/vaults/stc-kuwait/tables/*.md) documented 9 tables but
the live mock Oracle only had 2 (fct_prep_master, fct_prep_rev) with 4 rows each, so
the NL2SQL LLM frequently picked a non-existent table -> ORA-00942 -> silent failure.

Usage:
    python backend/scripts/seed_dummy_data.py            # truncate + reseed all
    python backend/scripts/seed_dummy_data.py --no-reset # insert without truncating

Connection (env-overridable; defaults match docker-compose.dev.yml mock):
    ORACLE_USER (stc) / ORACLE_PASSWORD (stc123) / ORACLE_DSN (localhost:1521/FREEPDB1)
"""

from __future__ import annotations

import glob
import os
import random
import re
import sys
from datetime import date, timedelta

import oracledb

SEED = 42
TODAY = date(2026, 6, 8)
VAULT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "vaults", "stc-kuwait", "tables"
)

NATIONALITIES = [
    "KUWAITI",
    "INDIAN",
    "EGYPTIAN",
    "FILIPINO",
    "BANGLADESHI",
    "SYRIAN",
    "PAKISTANI",
    "SAUDI",
]
REGIONS = ["Al Asimah", "Hawalli", "Farwaniya", "Ahmadi", "Jahra", "Mubarak Al-Kabeer"]
CATEGORIES = ["Consumer", "Business", "VIP"]
PLANS = ["Visa Plus 5", "Visa Plus 10", "Shabab Prepaid", "Hayyak", "eeZee Prepaid", "Tourist SIM"]
CALL_TYPES = ["VOICE", "DATA", "SMS", "VAS", "CONTENT"]
NETWORKS = ["STC-SA", "Zain-BH", "Etisalat-AE", "Ooredoo-QA", "Du-AE", "Vodafone-EG"]
PRODUCTS = [
    (1001, "PO-VOICE-01", "Voice", "Daily Voice 200min", "daily", "Voice", 200, 0.500),
    (1002, "PO-DATA-05", "Data", "5GB Weekly Pack", "weekly", "Data", 5, 2.000),
    (1003, "PO-DATA-20", "Data", "20GB Monthly Pack", "monthly", "Data", 20, 5.000),
    (1004, "PO-SOCIAL-01", "Data", "Social Unlimited", "monthly", "Social", 0, 3.000),
    (1005, "PO-COMBO-01", "Combo", "All-in-One 30", "monthly", "Combo", 30, 7.500),
    (1006, "PO-ROAM-01", "Roaming", "GCC Roaming 1GB", "weekly", "Roaming", 1, 4.000),
    (1007, "PO-VOICE-INTL", "Voice", "Intl Minutes 100", "monthly", "Voice", 100, 3.500),
    (1008, "PO-DATA-NIGHT", "Data", "Night Data 10GB", "monthly", "Data", 10, 1.500),
    (1009, "PO-SMS-01", "SMS", "SMS Bundle 500", "monthly", "SMS", 500, 1.000),
    (1010, "PO-DATA-100", "Data", "100GB Power Pack", "monthly", "Data", 100, 12.000),
    (1011, "PO-STARTER", "Combo", "Starter Pack", "monthly", "Combo", 5, 2.500),
    (1012, "PO-GAMING", "Data", "Gaming Pass", "monthly", "Gaming", 15, 4.500),
]


def parse_vault_columns(md_path: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (table_name, [(column, type)]) parsed from a vault .md file."""
    with open(md_path) as _fh:
        txt = _fh.read()
    m = re.search(r"^table:\s*(\S+)", txt, re.M)
    name = (m.group(1) if m else os.path.basename(md_path)[:-3]).lower()
    cols: list[tuple[str, str]] = []
    for line in txt.splitlines():
        mm = re.match(
            r"\s*\|\s*([A-Z0-9_]+)\s*\|\s*"
            r"(DATE|NUMBER|VARCHAR2|FLOAT|INT[A-Z]*|TIMESTAMP[A-Z ]*)\s*\|",
            line,
        )
        if mm:
            cols.append((mm.group(1), mm.group(2)))
    return name, cols


def ora_type(vault_type: str) -> str:
    if vault_type == "DATE" or vault_type.startswith("TIMESTAMP"):
        return "DATE"
    if vault_type in ("NUMBER", "FLOAT") or vault_type.startswith("INT"):
        return "NUMBER"
    return "VARCHAR2(400)"


def days_back(rng: random.Random, max_days: int, min_days: int = 0) -> date:
    return TODAY - timedelta(days=rng.randint(min_days, max_days))


def main() -> int:
    reset = "--no-reset" not in sys.argv
    rng = random.Random(SEED)

    conn = oracledb.connect(
        user=os.getenv("ORACLE_USER", "stc"),
        password=os.getenv("ORACLE_PASSWORD", "stc123"),
        dsn=os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1"),
    )
    cur = conn.cursor()

    schemas = {}
    for md in glob.glob(os.path.join(VAULT_DIR, "*.md")):
        name, cols = parse_vault_columns(md)
        if cols:
            schemas[name] = cols

    existing = {r[0].lower() for r in cur.execute("SELECT table_name FROM user_tables")}
    created = []
    for name, cols in schemas.items():
        if name not in existing:
            defs = ", ".join(f"{c} {ora_type(t)}" for c, t in cols)
            cur.execute(f"CREATE TABLE {name} ({defs})")
            created.append(name)
    conn.commit()
    print("Created tables:", created or "(none — all existed)")

    def real_cols(table: str) -> set[str]:
        return {
            r[0].upper()
            for r in cur.execute(
                "SELECT column_name FROM user_tab_columns WHERE table_name = :1",
                [table.upper()],
            )
        }

    def seed(table: str, rows: list[dict]) -> int:
        if not rows:
            return 0
        if reset:
            cur.execute(f"TRUNCATE TABLE {table}")
        cols = [c for c in rows[0] if c in real_cols(table)]
        ph = ", ".join(f":{i + 1}" for i in range(len(cols)))
        data = [[r.get(c) for c in cols] for r in rows]
        cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({ph})", data)
        conn.commit()
        return len(data)

    # Shared subscriber dimension (consistent CONTRNO/SUBNO across all tables).
    subs = []
    for i in range(80):
        nat = rng.choice(NATIONALITIES)
        subs.append(
            {
                "CONTRNO": f"C{100000 + i}",
                "SUBNO": f"9656{rng.randint(1000000, 9999999)}",
                "NATIONALITY": nat,
                "REGION": rng.choice(REGIONS),
                "APPDATE": days_back(rng, 540, 20),
                "PREPOST_PAID": rng.choices(["PREPAID", "POSTPAID"], [0.85, 0.15])[0],
                "CONTRACT_CATEGORY": rng.choice(CATEGORIES),
                "PLAN_ID": rng.randint(2001, 2006),
                "PLAN_NAME": rng.choice(PLANS),
                "NAT_GROUP": "GCC" if nat in ("KUWAITI", "SAUDI") else "EXPAT",
            }
        )

    counts = {}

    counts["fct_prep_master"] = seed(
        "fct_prep_master",
        [
            {
                "EXEC_DATE": TODAY,
                "SNAPSHOT_DATE": TODAY,
                "CONTRNO": s["CONTRNO"],
                "SUBNO": s["SUBNO"],
                "PREPOST_PAID": s["PREPOST_PAID"],
                "APPDATE": s["APPDATE"],
                "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                "NATIONALITY": s["NATIONALITY"],
                "NATIONALITY_GROUP": s["NAT_GROUP"],
                "REGION": s["REGION"],
                "MAIN_PLAN_NAME": s["PLAN_NAME"],
                "MAIN_PLAN_RENTAL": rng.choice([2, 5, 7.5, 10]),
                "ACTIVITY_STATUS": rng.choices(["ACTIVE", "DORMANT", "INACTIVE"], [0.7, 0.2, 0.1])[
                    0
                ],
                "L30D_IS_REVENUE_ACTIVE_BASE": rng.choice([0, 1]),
                "L30D_IS_ACTIVE_BASE": rng.choice(["Y", "N"]),
            }
            for s in subs
        ],
    )

    counts["fct_prep_master_hist"] = seed(
        "fct_prep_master_hist",
        [
            {
                "EXEC_DATE": TODAY - timedelta(days=30 * mb),
                "SNAPSHOT_DATE": TODAY - timedelta(days=30 * mb),
                "CONTRNO": s["CONTRNO"],
                "SUBNO": s["SUBNO"],
                "PREPOST_PAID": s["PREPOST_PAID"],
                "APPDATE": s["APPDATE"],
                "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                "NATIONALITY": s["NATIONALITY"],
                "NATIONALITY_GROUP": s["NAT_GROUP"],
                "REGION": s["REGION"],
                "ACTIVITY_STATUS": rng.choices(["ACTIVE", "DORMANT", "INACTIVE"], [0.7, 0.2, 0.1])[
                    0
                ],
                "L30D_IS_REVENUE_ACTIVE_BASE": rng.choice([0, 1]),
            }
            for s in subs
            for mb in range(6)
        ],
    )

    # PLAN_ID MUST be a real dim_prep_products.OFFER_ID and EXEC_DATE MUST span several
    # months, or "monthly revenue by region" (GROUP BY month, dp.BUSINESS via the
    # PLAN_ID=OFFER_ID join) collapses to a single NULL-region row. (Both were broken:
    # PLAN_ID was never inserted -> NULL join; EXEC_DATE was always TODAY -> one month.)
    counts["fct_prep_rev"] = seed(
        "fct_prep_rev",
        [
            (
                lambda s, p: {
                    "EXEC_DATE": TODAY - timedelta(days=30 * rng.randint(0, 11)),
                    "CONTRNO": s["CONTRNO"],
                    "SUBNO": s["SUBNO"],
                    "APPDATE": s["APPDATE"],
                    "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                    "NATIONALITY": s["NATIONALITY"],
                    "PREPOST_PAID": s["PREPOST_PAID"],
                    "PLAN_ID": p[0],  # -> dim_prep_products.OFFER_ID (join key)
                    "PLAN_NAME": p[3],  # matching product name (consistent with PLAN_ID)
                    "BS_TYPE": rng.choice(["GSM", "DATA"]),
                    "CDR_TYPE": rng.choice(CALL_TYPES),
                    "CHARGINGTYPE": rng.choice(["PREPAID", "HYBRID"]),
                    "BILLAMOUNT": round(rng.uniform(0.05, 45.0), 3),
                    "LOGDATE": days_back(rng, 360),
                    "CALLTYPE": rng.choice(CALL_TYPES),
                }
            )(rng.choice(subs), rng.choice(PRODUCTS))
            for _ in range(1600)
        ],
    )

    counts["dim_prep_products"] = seed(
        "dim_prep_products",
        [
            {
                "OFFER_ID": p[0],
                "PROD_OFFERING_ID": p[1],
                "BUSINESS": p[2],
                "PRODUCT_OFFER_NAME": p[3],
                "PRODUCT_VALIDITY": p[4],
                "PRODUCT_TYPE": p[5],
                "SUB_PRODUCT_TYPE": p[2],
                "PRODUCT_PRICE": p[7],
                "EQUIPID": f"EQ{p[0]}",
            }
            for p in PRODUCTS
        ],
    )

    counts["dim_prep_state_scd2"] = seed(
        "dim_prep_state_scd2",
        [
            {
                "EXEC_DATE": TODAY,
                "SNAPSHOT_DATE": TODAY,
                "SUBNO": s["SUBNO"],
                "APPDATE": s["APPDATE"],
                "PREPOST_PAID": s["PREPOST_PAID"],
                "EFFECTIVE_START_DATE": s["APPDATE"],
                "EFFECTIVE_END_DATE": None,
                "CURRENT_STATE": rng.choice(["ACTIVE", "SUSPENDED", "GRACE", "CHURNED"]),
                "PREPAID_BALANCE": round(rng.uniform(0, 60), 3),
            }
            for s in subs
        ],
    )

    counts["fct_prep_provision"] = seed(
        "fct_prep_provision",
        [
            (
                lambda s, p: {
                    "EXEC_DATE": TODAY,
                    "CONTRNO": s["CONTRNO"],
                    "SUBNO": s["SUBNO"],
                    "APPDATE": s["APPDATE"],
                    "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                    "NATIONALITY": s["NATIONALITY"],
                    "PREPOST_PAID": s["PREPOST_PAID"],
                    "BS_TYPE": rng.choice(["GSM", "DATA"]),
                    "PROD_OFFERING_ID": p[1],
                    "PRODUCT_OFFER_NAME": p[3],
                    "PRODUCT_TYPE": p[5],
                    "OFFER_ID": p[0],
                    "LOGDATE": days_back(rng, 360),
                    "ORDERSTATUS": rng.choices(["COMPLETED", "FAILED", "PENDING"], [0.8, 0.1, 0.1])[
                        0
                    ],
                }
            )(rng.choice(subs), rng.choice(PRODUCTS))
            for _ in range(500)
        ],
    )

    counts["fct_prep_recharge"] = seed(
        "fct_prep_recharge",
        [
            (
                lambda s: {
                    "EXEC_DATE": TODAY,
                    "CONTRNO": s["CONTRNO"],
                    "SUBNO": s["SUBNO"],
                    "APPDATE": s["APPDATE"],
                    "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                    "NATIONALITY": s["NATIONALITY"],
                    "PREPOST_PAID": s["PREPOST_PAID"],
                    "BS_TYPE": rng.choice(["GSM", "DATA"]),
                    "RECHARGE_DATE": days_back(rng, 360),
                    "PREPAIDBALANCEBEFORE": round(rng.uniform(0, 20), 3),
                    "TOPUP_AMOUNT": rng.choice([1, 2, 3, 5, 10, 15, 20, 30]),
                    "VOUCHER_TYPE": rng.choice(["ONLINE", "RETAIL", "ATM", "APP", "VOUCHER"]),
                    "OPERATEDBY": rng.choice(["ONLINE", "RETAIL", "ATM", "APP"]),
                }
            )(rng.choice(subs))
            for _ in range(700)
        ],
    )

    counts["fct_prep_roaming"] = seed(
        "fct_prep_roaming",
        [
            (
                lambda s: {
                    "EXEC_DATE": TODAY,
                    "CONTRNO": s["CONTRNO"],
                    "SUBNO": s["SUBNO"],
                    "APPDATE": s["APPDATE"],
                    "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                    "NATIONALITY": s["NATIONALITY"],
                    "PREPOST_PAID": s["PREPOST_PAID"],
                    "BS_TYPE": rng.choice(["GSM", "DATA"]),
                    "TRANSDATE": days_back(rng, 360),
                    "CALLTYPE": rng.choice(CALL_TYPES),
                    "USED_NETWORK": rng.choice(NETWORKS),
                    "OFFER_ID": rng.choice(PRODUCTS)[0],
                }
            )(rng.choice(subs))
            for _ in range(350)
        ],
    )

    kpis = [("VOICE_MIN", "Voice Minutes"), ("DATA_MB", "Data MB"), ("SMS_CNT", "SMS Count")]
    counts["fct_prep_usage"] = seed(
        "fct_prep_usage",
        [
            (
                lambda s, k: {
                    "EXEC_DATE": TODAY,
                    "CONTRNO": s["CONTRNO"],
                    "SUBNO": s["SUBNO"],
                    "APPDATE": s["APPDATE"],
                    "CONTRACT_CATEGORY": s["CONTRACT_CATEGORY"],
                    "NATIONALITY": s["NATIONALITY"],
                    "PREPOST_PAID": s["PREPOST_PAID"],
                    "PLAN_ID": s["PLAN_ID"],
                    "TRANSDATE": days_back(rng, 360),
                    "CATEGORY": rng.choice(["ONNET", "OFFNET", "INTL"]),
                    "NETWORK_DIRECTION": rng.choice(["MO", "MT"]),
                    "OPERATOR_NAME": "STC-KW",
                    "NETWORK_TYPE": rng.choice(["4G", "5G", "3G"]),
                    "KPI_TYPE": k[0],
                    "KPI_NAME": k[1],
                    "KPI_VALUE": round(rng.uniform(1, 5000), 2),
                }
            )(rng.choice(subs), rng.choice(kpis))
            for _ in range(900)
        ],
    )

    print("Seeded rows:", counts)

    # Self-check: "monthly revenue by region" must actually join AND span months.
    # Guards the exact regression we hit: fct_prep_rev.PLAN_ID NULL (join dead ->
    # single NULL-region row) or EXEC_DATE all one day (single month).
    regions, months = cur.execute(
        "SELECT COUNT(DISTINCT dp.BUSINESS), COUNT(DISTINCT TRUNC(fr.EXEC_DATE,'MM')) "
        "FROM fct_prep_rev fr JOIN dim_prep_products dp ON fr.PLAN_ID = dp.OFFER_ID"
    ).fetchone()
    print(f"Sanity: revenue-by-region joins -> {regions} region(s) x {months} month(s)")
    conn.close()
    if (regions or 0) < 2 or (months or 0) < 2:
        print("ERROR: revenue-by-region would collapse to one row — seeding is broken.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
