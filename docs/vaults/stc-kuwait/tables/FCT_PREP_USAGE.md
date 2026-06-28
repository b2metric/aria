---
table: FCT_PREP_USAGE
database: oracle
workspace: stc-kuwait
keywords: [data, kullanım, prepaid, sms, traffic, trafik, usage, use, voice]
generated_at: '2026-06-16T03:23:43.170686+00:00'
enriched_at: '2026-06-16T14:59:52.305624+00:00'
description: Fact table that keeps basic data, voice and SMS usage details of prepaid
  subscribers on the domestic network.
---

# FCT_PREP_USAGE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | NEXT_APPDATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | PLAN_ID | NUMBER | ✓ |  | Main tariff/plan ID | 
 | TRANSDATE | DATE | ✓ |  | Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs | 
 | CATEGORY | VARCHAR2 | ✓ |  | Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.) | 
 | NETWORK_DIRECTION | VARCHAR2 | ✓ |  | Network direction — classification such as on-net / off-net / international | 
 | OPERATOR_NAME | VARCHAR2 | ✓ |  | Name of the relevant operator — counterparty operator or guest network operator in case of roaming | 
| NETWORK_TYPE | VARCHAR2 | ✓ |  |  |
 | BILL_TYPE | VARCHAR2 | ✓ |  | Billing type — free, paid | 
 | KPI_TYPE | VARCHAR2 | ✓ |  | Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.) | 
 | KPI_NAME | VARCHAR2 | ✓ |  | Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.) | 
 | KPI_VALUE | NUMBER | ✓ |  | The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.) | 

## Keywords

## Business Metadata

**Description:** Fact table that keeps basic data, voice and SMS usage details of prepaid subscribers on the domestic network.

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

Ranks customers by total usage over 30 days. Usage is stored long/EAV-style: each row is one KPI,
so filter `KPI_TYPE = 'usage_volume'` and sum `KPI_VALUE` (the metric value), grouped by `CONTRNO`.
`LOGDATE` is the event date. Always pin the KPI filter — without it you sum unrelated metrics.

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

Monthly **data** usage by region. Pick data KPIs with `KPI_NAME LIKE '%DATA%'`, sum `KPI_VALUE`,
bucket by `TRUNC(LOGDATE,'MM')`, and JOIN `FCT_PREP_MASTER` on `CONTRNO` for `REGION`. Use
`KPI_NAME` (the readable metric name) for the data filter; `KPI_VALUE` carries the MB/volume.

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

## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
