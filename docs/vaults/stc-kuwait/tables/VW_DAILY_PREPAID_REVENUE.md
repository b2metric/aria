---
table: VW_DAILY_PREPAID_REVENUE
database: oracle
workspace: stc-kuwait
keywords: [account, billing, bundle, contract, country, customer, date, demographic, financial, geography, income, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, revenue, subscriber, tariff, temporal, time]
description: "View aggregating data for Daily Prepaid Revenue"
row_count: 4791
generated_at: 2026-07-01T22:36:31.233778+00:00
---

# VW_DAILY_PREPAID_REVENUE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| REVENUE_DATE | DATE | ✓ |  | Revenue Date |
| ACTIVATION_DATE | DATE | ✓ |  | Activation Date |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN (phone number) |
| CONTRNO | VARCHAR2 | ✓ |  | Contract number (subscriber identifier) |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (Individual, Corporate, VIP) |
| NATIONALITY | VARCHAR2 | ✓ |  | Customer nationality |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Prepost Paid |
| PLAN_ID | VARCHAR2 | ✓ |  | Plan Id |
| PLAN_NAME | VARCHAR2 | ✓ |  | Plan Name |
| BS_TYPE | VARCHAR2 | ✓ |  | Basic service type (Voice, Data, M2M) |
| REVENUE_CATEGORY | VARCHAR2 | ✓ |  | Revenue Category |
| PREPAID_REVENUE | NUMBER | ✓ |  | Prepaid Revenue |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:36:31.234305+00:00*

- **BS_TYPE**: `DATA`, `FIBER`, `FWA`, `VOICE`
- **CONTRACT_CATEGORY**: `INDIVIDUAL`, `Individual Premium`
- **NATIONALITY**: `BGD`, `EGY`, `IND`, `KWT`, `NPL`, `PHL`, `SDN`, `SYR`
- **PLAN_ID**: `PLUS1T`, `PRED2T`, `STCALL0`, `STCALLT`, `VIVALLT`
- **PLAN_NAME**: `Pre KD1+1 30D PLN`, `Pre KD5 30D PLN`, `Pre KD6 30D PLN`, `Pre net KD8 1TB 2M PLN`, `go 0KD Prepaid Plan`
- **PREPOST_PAID**: `POST`, `PREP`
- **REVENUE_CATEGORY**: `OTHER`, `PAYG`, `ROAMING`, `VAS`

<!-- ARIA:ENUM-VALUES-END -->
