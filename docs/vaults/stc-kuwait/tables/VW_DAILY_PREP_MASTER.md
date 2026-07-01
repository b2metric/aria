---
table: VW_DAILY_PREP_MASTER
database: oracle
workspace: stc-kuwait
keywords: [360 view, account, bandwidth, batch, billing, bundle, call, churn, contract, country, customer, data, date, demographic, etl, financial, geography, income, internet, lifecycle, master, minutes, money, nationality, offer, package, payment, prepaid, product, retention, revenue, snapshot, state, status, subscriber, tariff, temporal, time, usage, voice]
description: "View aggregating data for Daily Prep Master"
row_count: 400
generated_at: 2026-07-01T22:36:31.234962+00:00
---

# VW_DAILY_PREP_MASTER

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| SNAPSHOT_DATE | DATE | ✓ |  | Data snapshot date |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Prepost Paid |
| TENURE_BUCKET | VARCHAR2 | ✓ |  | Tenure Bucket |
| ID_TYPE | VARCHAR2 | ✓ |  | Id Type |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (Individual, Corporate, VIP) |
| NATIONALITY | VARCHAR2 | ✓ |  | Customer nationality |
| BS_TYPE | VARCHAR2 | ✓ |  | Basic service type (Voice, Data, M2M) |
| BS_FLAG | VARCHAR2 | ✓ |  | Bs Flag |
| NUM_TYPE | VARCHAR2 | ✓ |  | Num Type |
| PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Prepaid State Group |
| MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Main Plan Prod Offering Id |
| MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | Main Plan Name |
| MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | Main Plan Equipid |
| MAIN_PLAN_RENTAL | VARCHAR2 | ✓ |  | Main Plan Rental |
| CHURN_FLAG | VARCHAR2 | ✓ |  | Churn Flag |
| LAST_BUNDLE_NAME | VARCHAR2 | ✓ |  | Last Bundle Name |
| LAST_BUNDLE_BILLAMOUNT | VARCHAR2 | ✓ |  | Billed amount (revenue) |
| ACTV_BUNDLES | VARCHAR2 | ✓ |  | Actv Bundles |
| NO_USAGE_BUCKET | VARCHAR2 | ✓ |  | No Usage Bucket |
| DATA_BUCKET | VARCHAR2 | ✓ |  | Data Bucket |
| VOICE_OUT_BUCKET | VARCHAR2 | ✓ |  | Voice Out Bucket |
| ACTIVE_BUNDLE_FLAG | VARCHAR2 | ✓ |  | Active Bundle Flag |
| L1D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L1D Revenue Flag |
| L7D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L7D Revenue Flag |
| L15D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L15D Revenue Flag |
| L30D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L30D Revenue Flag |
| L90D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L90D Revenue Flag |
| L120D_REVENUE_FLAG | VARCHAR2 | ✓ |  | L120D Revenue Flag |
| L1D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L1D Active Flag |
| L7D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L7D Active Flag |
| L15D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L15D Active Flag |
| L30D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L30D Active Flag |
| L90D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L90D Active Flag |
| L120D_ACTIVE_FLAG | VARCHAR2 | ✓ |  | L120D Active Flag |
| PREP_BAL_AT_MONTH_START | NUMBER | ✓ |  | Prep Bal At Month Start |
| PREP_BAL_AT_PREV_MONTH_START | NUMBER | ✓ |  | Prep Bal At Prev Month Start |
| PREP_BAL_AS_OF_TODAY | NUMBER | ✓ |  | Prep Bal As Of Today |
| SUBS_COUNT | NUMBER | ✓ |  | Subs Count |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:36:31.235258+00:00*

- **ACTIVE_BUNDLE_FLAG**: `NO`
- **ACTV_BUNDLES**: `Hajj Free Bundle 15 Days | Pre KD5 30GB 100LocalMin 30D BUN V3`, `Pre KD0 1M VAL`, `Pre KD0 1M VAL | Pre KD6 65GB 100LocalMin 28D BUN V2`, `Pre KD0 1M VAL | Unique go 5`, `Pre KD0 1M VAL | go 6`, `Pre KD0 1M VAL | go 9`, `Pre KD0 1M VAL | go Super KD5`, `Pre KD4 3M VAL`, `Pre KD6 65GB 100LocalMin 28D BUN V2`, `Select go 5`, `go 6`, `go Super KD5`, `go special KD5`
- **BS_FLAG**: `MAIN`
- **BS_TYPE**: `DATA`, `FIBER`, `VOICE`
- **CHURN_FLAG**: `CHURN`
- **CONTRACT_CATEGORY**: `INDIVIDUAL`, `Individual Premium`
- **DATA_BUCKET**: `Churned`
- **ID_TYPE**: `A`, `C`, `D`, `E`, `G`, `P`, `R`, `X`
- **L120D_ACTIVE_FLAG**: `NO`, `YES`
- **L120D_REVENUE_FLAG**: `NO`, `YES`
- **L15D_ACTIVE_FLAG**: `NO`, `YES`
- **L15D_REVENUE_FLAG**: `NO`, `YES`
- **L1D_ACTIVE_FLAG**: `NO`, `YES`
- **L1D_REVENUE_FLAG**: `NO`, `YES`
- **L30D_ACTIVE_FLAG**: `NO`, `YES`
- **L30D_REVENUE_FLAG**: `NO`, `YES`
- **L7D_ACTIVE_FLAG**: `NO`, `YES`
- **L7D_REVENUE_FLAG**: `NO`, `YES`
- **L90D_ACTIVE_FLAG**: `NO`, `YES`
- **L90D_REVENUE_FLAG**: `NO`, `YES`
- **NATIONALITY**: `BGD`, `EGY`, `IND`, `KWT`, `NPL`, `PHL`, `SDN`, `SYR`
- **NO_USAGE_BUCKET**: `Churned`
- **NUM_TYPE**: `1`, `2`, `3`, `4`, `5`, `B`, `G`, `H`, `P`, `S`, `V`
- **PREPAID_STATE_GROUP**: `ACTIVE`, `CHURN_WITHIN_MONTH`, `DISABLE`, `GRACE`, `HISTORICAL_CHURN`, `IDLE`, `POOL`, `PREP_TO_POST`
- **PREPOST_PAID**: `POST`, `PREP`
- **TENURE_BUCKET**: `1.0–30 Days (New Customer)`, `2.30–60 Days (Early Lifecycle)`, `3.60–90 Days (Growing Customer)`, `4.90–120 Days (Maturing Customer)`, `5.>120 Days (Established Customer)`
- **VOICE_OUT_BUCKET**: `Churned`

<!-- ARIA:ENUM-VALUES-END -->
