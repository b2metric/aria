---
table: FCT_PREP_RECHARGE
database: oracle
workspace: stc-kuwait
keywords: [TL loading, TL yükleme, balance, ball up, loading, payment, prepaid, recharge,
  top up, top-up, yükleme]
generated_at: '2026-06-16T03:23:43.169499+00:00'
enriched_at: '2026-06-16T14:59:52.300825+00:00'
description: Fact table showing the details and amounts of top-up, recharge transactions
  of prepaid subscribers.
---

# FCT_PREP_RECHARGE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | SUBSCRIBERID | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
 | RECHARGE_DATE | DATE | ✓ |  | Date/time stamp when KD upload occurred | 
 | PREPAIDBALANCEBEFORE | NUMBER | ✓ |  | Main balance in the account before recharge. | 
 | TOPUP_SEQ | NUMBER | ✓ |  | Sequence number of the upload process — the unique identifier (primary key) of the process | 
| SERIAL_NUMBER | VARCHAR2 | ✓ |  |  |
 | ITEM_CODE | VARCHAR2 | ✓ |  | Installation product code — e.g. code of a specific voucher type or download package | 
 | ITEM_NO | VARCHAR2 | ✓ |  | ITEM serial number — tracking number used for stock system reference purposes | 
 | VOUCHER_TYPE | VARCHAR2 | ✓ |  | Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.) | 
 | TOPUP_AMOUNT | NUMBER | ✓ |  | Loaded amount (KD) | 
| OPERATEDBY | VARCHAR2 | ✓ |  |  |
| THIRDPARTYNUMBER | VARCHAR2 | ✓ |  |  |
| TRADETYPE | VARCHAR2 | ✓ |  |  |
| ACCESSMETHOD | VARCHAR2 | ✓ |  |  |
| CHANNEL | VARCHAR2 | ✓ |  |  |
| CHANNELNAME | VARCHAR2 | ✓ |  |  |
 | TOPUP_SEQ_HASH | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 

## Keywords

## Business Metadata

**Description:** Fact table showing the details and amounts of top-up, recharge transactions of prepaid subscribers.

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

Ranks **customers** by total top-up over the last 30 days. Group by `CONTRNO` (the customer /
contract — stable for the subscriber's lifetime), sum `TOPUP_AMOUNT`, and use `RECHARGE_DATE` as
the date. "Customer" ⇒ `CONTRNO`; if the question says "line" or "MSISDN" use `SUBNO` instead.

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

### Q: Month-over-month recharge revenue change buckets (per line, full sub-buckets)

**This is the CANONICAL pattern for "recharge MoM report by bucket".** Use this table
(`FCT_PREP_RECHARGE`), the `TOPUP_AMOUNT` column, and **per `SUBNO`** ("# of lines" = unique
SUBNO, the MSISDN/line — NOT CONTRNO). Do NOT use FCT_PREP_REV / BILLAMOUNT (that is billed
charges, not prepaid topups). Classify each line ONCE, then `GROUP BY revenue_bucket` only —
never group by SUBNO in the final aggregate or every bucket collapses to 1 line.

Rules this query implements (match them exactly):
- **Same**: revenue change within ±0.99%.
- **Increased**: 1-10 / 11-20 / 21-50 / 51-80 / 81-100 / >100 % (contiguous `<=` chains, no gaps).
- **Decreased**: 1-10 / 11-20 / 21-50 / 51-80 / 81-99 %.
- **Zeroed** (was active, now 0 this month): split by CONSECUTIVE zero months — 1 / 2 / 3 / >3.
- **Resurrected** (active now, prior month 0): split by GAP length before resurrection — 1 / 2 / 3 / >3.
- For Zeroed & Resurrected, **"previous revenue" = the most recent NON-ZERO month's revenue**,
  not last month's 0. (That's what `last_nonzero_rev` / `MONTHS_BETWEEN(...)` compute.)
- Per bucket output: `# unique lines`, previous revenue, current revenue, delta.
- Pull ≥12 months of history (here 2025-01) so the consecutive/gap counts are real.

To run a different month: change the three date literals — current `'2026-05-01'`, prior
`'2026-04-01'`, history floor `'2025-01-01'`.

```sql
WITH monthly AS (
    SELECT SUBNO,
           TRUNC(RECHARGE_DATE, 'MM') AS rev_month,
           SUM(TOPUP_AMOUNT)          AS rev
    FROM   FCT_PREP_RECHARGE
    WHERE  RECHARGE_DATE >= DATE '2025-01-01'
      AND  RECHARGE_DATE <  DATE '2026-06-01'
    GROUP  BY SUBNO, TRUNC(RECHARGE_DATE, 'MM')
),
per_line AS (
    SELECT SUBNO,
           NVL(MAX(CASE WHEN rev_month = DATE '2026-05-01' THEN rev END), 0) AS curr_rev,
           NVL(MAX(CASE WHEN rev_month = DATE '2026-04-01' THEN rev END), 0) AS prior_rev,
           MAX(CASE WHEN rev_month < DATE '2026-05-01' THEN rev_month END)   AS last_nonzero_month
    FROM   monthly
    GROUP  BY SUBNO
),
joined AS (
    SELECT pl.SUBNO, pl.curr_rev, pl.prior_rev,
           m.rev AS last_nonzero_rev,
           CASE WHEN pl.last_nonzero_month IS NOT NULL
                THEN MONTHS_BETWEEN(DATE '2026-05-01', pl.last_nonzero_month) END AS months_since_nonzero
    FROM   per_line pl
    LEFT   JOIN monthly m ON m.SUBNO = pl.SUBNO AND m.rev_month = pl.last_nonzero_month
),
classified AS (
    SELECT SUBNO, curr_rev,
           CASE WHEN curr_rev > 0 AND prior_rev > 0 THEN prior_rev ELSE last_nonzero_rev END AS previous_revenue,
           CASE
               WHEN curr_rev = 0 AND last_nonzero_rev IS NOT NULL THEN
                   CASE WHEN months_since_nonzero = 1 THEN 'Zeroed (1 Month)'
                        WHEN months_since_nonzero = 2 THEN 'Zeroed (2 Consecutive Months)'
                        WHEN months_since_nonzero = 3 THEN 'Zeroed (3 Consecutive Months)'
                        ELSE 'Zeroed (>3 Consecutive Months)' END
               WHEN curr_rev > 0 AND prior_rev = 0 AND last_nonzero_rev IS NOT NULL THEN
                   CASE WHEN months_since_nonzero - 1 = 1 THEN 'Resurrected (After 1 Month Gap)'
                        WHEN months_since_nonzero - 1 = 2 THEN 'Resurrected (After 2 Months Gap)'
                        WHEN months_since_nonzero - 1 = 3 THEN 'Resurrected (After 3 Months Gap)'
                        ELSE 'Resurrected (After >3 Months Gap)' END
               WHEN curr_rev > 0 AND last_nonzero_rev IS NULL THEN 'New'
               WHEN curr_rev > 0 AND prior_rev > 0 THEN
                   CASE
                       WHEN ABS((curr_rev - prior_rev) / prior_rev) <= 0.0099 THEN 'Same'
                       WHEN (curr_rev / prior_rev) - 1 > 0 THEN
                           CASE WHEN (curr_rev/prior_rev)-1 <= 0.10 THEN 'Increased (1-10%)'
                                WHEN (curr_rev/prior_rev)-1 <= 0.20 THEN 'Increased (11-20%)'
                                WHEN (curr_rev/prior_rev)-1 <= 0.50 THEN 'Increased (21-50%)'
                                WHEN (curr_rev/prior_rev)-1 <= 0.80 THEN 'Increased (51-80%)'
                                WHEN (curr_rev/prior_rev)-1 <= 1.00 THEN 'Increased (81-100%)'
                                ELSE 'Increased (>100%)' END
                       ELSE
                           CASE WHEN ABS((curr_rev/prior_rev)-1) <= 0.10 THEN 'Decreased (1-10%)'
                                WHEN ABS((curr_rev/prior_rev)-1) <= 0.20 THEN 'Decreased (11-20%)'
                                WHEN ABS((curr_rev/prior_rev)-1) <= 0.50 THEN 'Decreased (21-50%)'
                                WHEN ABS((curr_rev/prior_rev)-1) <= 0.80 THEN 'Decreased (51-80%)'
                                ELSE 'Decreased (81-99%)' END
                   END
               ELSE 'Excluded' END AS revenue_bucket
    FROM joined
)
SELECT revenue_bucket,
       COUNT(DISTINCT SUBNO)                    AS unique_lines,
       SUM(previous_revenue)                    AS previous_total_revenue,
       SUM(curr_rev)                            AS current_total_revenue,
       SUM(curr_rev - NVL(previous_revenue, 0)) AS delta_revenue
FROM   classified
WHERE  revenue_bucket <> 'Excluded'
GROUP  BY revenue_bucket
ORDER  BY revenue_bucket
```

### Q: Year-over-year month-to-date recharge (e.g. June 2025 vs June 2026, day 1–21)

Compares the **same calendar window** across two years — here June 1–21 of 2025 vs 2026 — so a
partial (in-progress) month is judged fairly against the prior year's equivalent days. Returns
distinct recharging lines and total `TOPUP_AMOUNT` for each window plus the delta. To retarget,
change only the four date literals (window start/end for each year); the upper bound is exclusive
(`< day 22` ⇒ through day 21).

```sql
WITH mtd AS (
    SELECT SUBNO,
           SUM(CASE WHEN RECHARGE_DATE >= DATE '2025-06-01' AND RECHARGE_DATE < DATE '2025-06-22'
                    THEN TOPUP_AMOUNT ELSE 0 END) AS jun_prev,
           SUM(CASE WHEN RECHARGE_DATE >= DATE '2026-06-01' AND RECHARGE_DATE < DATE '2026-06-22'
                    THEN TOPUP_AMOUNT ELSE 0 END) AS jun_curr
    FROM   FCT_PREP_RECHARGE
    WHERE  RECHARGE_DATE >= DATE '2025-06-01' AND RECHARGE_DATE < DATE '2026-06-22'
    GROUP  BY SUBNO
)
SELECT COUNT(DISTINCT CASE WHEN jun_prev > 0 THEN SUBNO END) AS lines_prev_mtd,
       COUNT(DISTINCT CASE WHEN jun_curr > 0 THEN SUBNO END) AS lines_curr_mtd,
       SUM(jun_prev) AS revenue_prev_mtd,
       SUM(jun_curr) AS revenue_curr_mtd,
       SUM(jun_curr - jun_prev) AS delta_revenue
FROM   mtd
```

## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
