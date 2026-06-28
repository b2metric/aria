#!/usr/bin/env python3
"""enrich-vault-stc.py — append domain mapping + few-shot example queries to
the STC Kuwait vault's FCT_PREP_* tables.

Why
---
Phase 1+2 made the SQL pipeline more aggressive about delegating to the LLM
and semantically re-ranked tables via Qdrant. But the LLM still only sees what
the md files contain — and the STC tables documented their columns without
documenting their *cross-table semantics*. The result: questions like "monthly
recharge revenue bucket comparison" picked FCT_PREP_REV (substring "REV"
match) instead of FCT_PREP_RECHARGE (the actual topup table), and answers had
no canonical "MoM bucket SQL" shape to anchor on.

This script appends two sections to each relevant table:

  ## Domain Mapping            -- which user phrases route to this table
  ## Example Queries           -- 2-3 canonical Q→SQL examples

Both sections are picked up by the existing vault retriever (the whole md
content is embedded) AND by the LLM schema-context builder (it reads
descriptions and table-level notes). Sentinel: '<!-- ARIA:ENRICH-V1 -->'.

Idempotent — re-running is a no-op once the sentinel is present.

Usage
-----
On the target Mac:
    cd ~/projects/b2metric-aria
    python3 scripts/enrich-vault-stc.py
    docker compose -f docker-compose.dev.yml restart backend
    # if Phase 2 is also applied, re-trigger vault sync to refresh embeddings:
    #   POST /api/workspaces/stc-kuwait/sync   (or just wait for the next query
    #   — auto-index runs once)
"""

from __future__ import annotations

import pathlib
import sys

REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
VAULT_DIR = REPO_DIR / "docs" / "vaults" / "stc-kuwait" / "tables"

SENTINEL = "<!-- ARIA:ENRICH-V1 -->"

# ── per-table enrichment blocks ──────────────────────────────────────────────
# Each value is appended verbatim to the bottom of <table>.md if SENTINEL
# is absent. Keep blocks self-contained and SQL syntactically valid Oracle.

ENRICH: dict[str, str] = {}

ENRICH["FCT_PREP_RECHARGE"] = """

<!-- ARIA:ENRICH-V1 -->
## Domain Mapping

This table is the source of truth for **subscriber recharge / topup revenue**.

| User phrase | Pick this table because |
|---|---|
| "revenue" (when context is prepaid / topups / loads) | `TOPUP_AMOUNT` is the recharge value |
| "topup", "recharge", "load", "reload" | direct match |
| "arpu" | `SUM(TOPUP_AMOUNT) / COUNT(DISTINCT SUBNO)` |
| "monthly revenue change buckets" / "MoM revenue analysis" | canonical SQL below |

NOT this table for: billing/charged amount (use `FCT_PREP_REV`), usage volume (use `FCT_PREP_USAGE`).

## Example Queries

### Q: Top 10 customers by recharge in the last 30 days

```sql
SELECT
    CONTRNO,
    SUM(TOPUP_AMOUNT) AS total_recharge,
    COUNT(*)          AS recharge_count
FROM FCT_PREP_RECHARGE
WHERE RECHARGE_DATE >= TRUNC(SYSDATE) - 30
GROUP BY CONTRNO
ORDER BY total_recharge DESC
FETCH FIRST 10 ROWS ONLY
```

### Q: Monthly revenue trend by region (last 6 months)

Requires a JOIN with `FCT_PREP_MASTER` (where region/nationality lives):

```sql
SELECT
    TRUNC(r.RECHARGE_DATE, 'MM') AS month,
    m.REGION,
    SUM(r.TOPUP_AMOUNT)          AS total_revenue
FROM FCT_PREP_RECHARGE r
JOIN FCT_PREP_MASTER  m ON r.CONTRNO = m.CONTRNO
WHERE r.RECHARGE_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
GROUP BY TRUNC(r.RECHARGE_DATE, 'MM'), m.REGION
ORDER BY month, m.REGION
```

### Q: Month-over-month revenue change buckets (Zeroed / Resurrected / Same / Increased / Decreased)

Canonical "bucket analysis" pattern — single query, conditional aggregation, FULL OUTER JOIN to capture entries that appear in only one of the two periods:

```sql
WITH sub_monthly AS (
    SELECT
        SUBNO,
        TRUNC(RECHARGE_DATE, 'MM') AS rev_month,
        SUM(TOPUP_AMOUNT)          AS total_recharge
    FROM FCT_PREP_RECHARGE
    WHERE RECHARGE_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3)
    GROUP BY SUBNO, TRUNC(RECHARGE_DATE, 'MM')
),
prev_curr AS (
    SELECT
        NVL(p.SUBNO, c.SUBNO)         AS SUBNO,
        NVL(p.total_recharge, 0)      AS prev_rev,
        NVL(c.total_recharge, 0)      AS curr_rev
    FROM (SELECT * FROM sub_monthly WHERE rev_month = TRUNC(ADD_MONTHS(SYSDATE, -1), 'MM')) p
    FULL OUTER JOIN
         (SELECT * FROM sub_monthly WHERE rev_month = TRUNC(SYSDATE, 'MM')) c
      ON p.SUBNO = c.SUBNO
),
bucketed AS (
    SELECT
        SUBNO, prev_rev, curr_rev,
        CASE
            WHEN prev_rev > 0 AND curr_rev = 0                         THEN 'Zeroed'
            WHEN prev_rev = 0 AND curr_rev > 0                         THEN 'Resurrected'
            WHEN prev_rev > 0 AND ABS((curr_rev - prev_rev) / prev_rev) < 0.01 THEN 'Same'
            WHEN prev_rev > 0 AND curr_rev > prev_rev THEN
                CASE WHEN (curr_rev / prev_rev) - 1 <= 0.10 THEN 'Increased (1-10%)'
                     WHEN (curr_rev / prev_rev) - 1 <= 0.50 THEN 'Increased (11-50%)'
                     ELSE                                        'Increased (>50%)'
                END
            WHEN prev_rev > 0 AND curr_rev < prev_rev THEN
                CASE WHEN ABS((curr_rev / prev_rev) - 1) <= 0.10 THEN 'Decreased (1-10%)'
                     WHEN ABS((curr_rev / prev_rev) - 1) <= 0.50 THEN 'Decreased (11-50%)'
                     ELSE                                              'Decreased (>50%)'
                END
            ELSE 'Other'
        END AS revenue_bucket
    FROM prev_curr
)
SELECT
    revenue_bucket,
    COUNT(DISTINCT SUBNO) AS unique_lines,
    SUM(prev_rev)         AS previous_total,
    SUM(curr_rev)         AS current_total,
    SUM(curr_rev - prev_rev) AS delta
FROM bucketed
GROUP BY revenue_bucket
ORDER BY revenue_bucket
```
"""

ENRICH["FCT_PREP_USAGE"] = """

<!-- ARIA:ENRICH-V1 -->
## Domain Mapping

Generic KPI fact — every measurable usage metric lives here, identified by `KPI_TYPE` + `KPI_NAME`.

| User phrase | Filter |
|---|---|
| "volume" (usage) | `KPI_TYPE = 'usage_volume'` |
| "duration / minutes" | `KPI_TYPE = 'usage_duration'` |
| "count / transactions" | `KPI_TYPE = 'usage_count'` (NOT `COUNT(*)`) |
| "revenue" (KPI-recorded) | `KPI_TYPE = 'revenue'` — but for topup revenue prefer `FCT_PREP_RECHARGE` |
| "data / MB / GB" | `KPI_NAME LIKE '%DATA%'` |
| "voice minutes" | `KPI_NAME LIKE '%VOICE%MIN%'` |
| "SMS count" | `KPI_NAME LIKE '%SMS%CNT%'` |
| "roaming" | check `FCT_PREP_ROAMING` instead for richer breakdown |

`KPI_VALUE` semantics depend on `KPI_NAME` (MB, minutes, count, TL). Don't sum across KPI_NAMEs of different units.

## Example Queries

### Q: Top 10 customers by total usage volume (last 30 days)

```sql
SELECT
    CONTRNO,
    SUM(KPI_VALUE) AS total_volume
FROM FCT_PREP_USAGE
WHERE KPI_TYPE = 'usage_volume'
  AND LOGDATE >= TRUNC(SYSDATE) - 30
GROUP BY CONTRNO
ORDER BY total_volume DESC
FETCH FIRST 10 ROWS ONLY
```

### Q: Data usage by region — monthly trend

```sql
SELECT
    TRUNC(u.LOGDATE, 'MM')   AS month,
    m.REGION,
    SUM(u.KPI_VALUE)         AS total_data_mb
FROM FCT_PREP_USAGE u
JOIN FCT_PREP_MASTER m ON u.CONTRNO = m.CONTRNO
WHERE u.KPI_NAME LIKE '%DATA%'
  AND u.LOGDATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
GROUP BY TRUNC(u.LOGDATE, 'MM'), m.REGION
ORDER BY month, m.REGION
```
"""

ENRICH["FCT_PREP_PROVISION"] = """

<!-- ARIA:ENRICH-V1 -->
## Domain Mapping

Subscription / provisioning event log. Each row = one subscribe / unsubscribe / renewal event.

| User phrase | Filter |
|---|---|
| "subscribed bundles" | `PRODUCT_TYPE = 'Bundles'` — **plural**, NOT `'Bundle'` (verified from live DB) |
| "add-ons" | `PRODUCT_TYPE = 'AddOns'` |
| "devices" | `PRODUCT_TYPE = 'Device'` |
| "top subscribed X" | use `COUNT(DISTINCT SUBNO)` — counts *subscribers* not events |

For period-over-period comparisons of subscriptions, use conditional aggregation in one query.

## Example Queries

### Q: Top 10 subscribed bundles in the last 30 days vs previous 30 days

```sql
SELECT
    PRODUCT_OFFER_NAME,
    COUNT(DISTINCT CASE
        WHEN LOGDATE >= TRUNC(SYSDATE) - 30                          THEN SUBNO END) AS last_30d_subs,
    COUNT(DISTINCT CASE
        WHEN LOGDATE >= TRUNC(SYSDATE) - 60
         AND LOGDATE <  TRUNC(SYSDATE) - 30                          THEN SUBNO END) AS prev_30d_subs,
    COUNT(DISTINCT CASE
        WHEN LOGDATE >= TRUNC(SYSDATE) - 30                          THEN SUBNO END)
  - COUNT(DISTINCT CASE
        WHEN LOGDATE >= TRUNC(SYSDATE) - 60
         AND LOGDATE <  TRUNC(SYSDATE) - 30                          THEN SUBNO END) AS delta
FROM FCT_PREP_PROVISION
WHERE LOGDATE >= TRUNC(SYSDATE) - 60
  AND PRODUCT_TYPE = 'Bundles'
GROUP BY PRODUCT_OFFER_NAME
ORDER BY last_30d_subs DESC
FETCH FIRST 10 ROWS ONLY
```

### Q: Daily bundle subscription trend (last 30 days)

```sql
SELECT
    TRUNC(LOGDATE) AS day,
    COUNT(DISTINCT SUBNO) AS new_subscribers
FROM FCT_PREP_PROVISION
WHERE PRODUCT_TYPE = 'Bundles'
  AND LOGDATE >= TRUNC(SYSDATE) - 30
GROUP BY TRUNC(LOGDATE)
ORDER BY day
```
"""

ENRICH["FCT_PREP_REV"] = """

<!-- ARIA:ENRICH-V1 -->
## Domain Mapping

**Billing / charge events.** This is NOT the topup table.

| User phrase | Pick this table because |
|---|---|
| "billing", "charged amount", "bill amount" | `BILLAMOUNT` is the charged value |
| "content rental" | `CONTENT_RENTAL` column lives here |

NOT this table for: "revenue" in the topup/recharge sense → use `FCT_PREP_RECHARGE`. The substring "REV" in this name has misled the keyword-only matcher; semantic retrieval (Phase 2) should resolve this, and the glossary above confirms which is which.

## Example Queries

### Q: Monthly billing by region

```sql
SELECT
    TRUNC(r.LOGDATE, 'MM') AS month,
    m.REGION,
    SUM(r.BILLAMOUNT)      AS total_billing
FROM FCT_PREP_REV r
JOIN FCT_PREP_MASTER m ON r.CONTRNO = m.CONTRNO
WHERE r.LOGDATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
GROUP BY TRUNC(r.LOGDATE, 'MM'), m.REGION
ORDER BY month, m.REGION
```
"""


def enrich() -> dict[str, str]:
    if not VAULT_DIR.exists():
        sys.exit(f"vault dir not found: {VAULT_DIR}")
    results: dict[str, str] = {}
    for table_name, block in ENRICH.items():
        md_path = VAULT_DIR / f"{table_name}.md"
        if not md_path.exists():
            results[table_name] = "missing"
            continue
        src = md_path.read_text()
        if SENTINEL in src:
            results[table_name] = "already enriched"
            continue
        new_src = src.rstrip() + block
        md_path.write_text(new_src)
        results[table_name] = "enriched"
    return results


if __name__ == "__main__":
    res = enrich()
    width = max(len(k) for k in res) + 2
    for tbl, status in res.items():
        marker = {"enriched": "+", "already enriched": ".", "missing": "?"}.get(status, " ")
        print(f"  {marker} {tbl.ljust(width)} {status}")
    print("\nnext:")
    print("  docker compose -f docker-compose.dev.yml restart backend")
    print("  # then trigger workspace re-sync (re-embeds enriched md files):")
    print("  # POST /api/workspaces/stc-kuwait/sync   via Admin UI")
    print("  # OR just send any question -- Qdrant auto-indexes on first call")
