---
table: VW_DAILY_PREP_RECHARGE
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, balance, bandwidth, batch, billing, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, income, internet, mobile, money, msisdn, nationality, payment, phone number, prepaid, recharge, revenue, snapshot, subscriber, temporal, time, topup, touchpoint, usage]
description: "View aggregating data for Daily Prep Recharge"
row_count: 3441
generated_at: 2026-07-01T22:36:31.235699+00:00
---

# VW_DAILY_PREP_RECHARGE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | ETL execution date |
| RECHARGE_DATE | DATE | ✓ |  | Recharge Date |
| CONTRNO | VARCHAR2 | ✓ |  | Contract number (subscriber identifier) |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN (phone number) |
| ACTIVATION_DATE | DATE | ✓ |  | Activation Date |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (Individual, Corporate, VIP) |
| NATIONALITY | VARCHAR2 | ✓ |  | Customer nationality |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Prepost Paid |
| SUBSCRIBERID | VARCHAR2 | ✓ |  | Subscriberid |
| BS_TYPE | VARCHAR2 | ✓ |  | Basic service type (Voice, Data, M2M) |
| PREPAIDBALANCEBEFORE | NUMBER | ✓ |  | Prepaidbalancebefore |
| TOPUP_SEQ | NUMBER | ✓ |  | Topup Seq |
| SERIAL_NUMBER | VARCHAR2 | ✓ |  | Serial Number |
| ITEM_CODE | VARCHAR2 | ✓ |  | Item Code |
| ITEM_NO | VARCHAR2 | ✓ |  | Item No |
| VOUCHER_TYPE | VARCHAR2 | ✓ |  | Voucher Type |
| OPERATEDBY | VARCHAR2 | ✓ |  | Operatedby |
| THIRDPARTYNUMBER | VARCHAR2 | ✓ |  | Thirdpartynumber |
| TRADETYPE | VARCHAR2 | ✓ |  | Tradetype |
| ACCESSMETHOD | VARCHAR2 | ✓ |  | Accessmethod |
| CHANNEL | VARCHAR2 | ✓ |  | Transaction channel |
| CHANNELNAME | VARCHAR2 | ✓ |  | Transaction channel |
| TOPUP_SEQ_HASH | NUMBER | ✓ |  | Topup Seq Hash |
| RECHARGE_TYPE | VARCHAR2 | ✓ |  | Recharge Type |
| RECHARGE_SUB_TYPE | VARCHAR2 | ✓ |  | Recharge Sub Type |
| DENOMINATION | VARCHAR2 | ✓ |  | Denomination |
| AMOUNT | NUMBER | ✓ |  | Amount |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:36:31.235905+00:00*

- **ACCESSMETHOD**: `0`, `1`, `3`, `4`, `5`, `6`
- **BS_TYPE**: `DATA`, `FIBER`, `VOICE`
- **CHANNEL**: `DIGITAL CHANNEL`, `E-DEALERS RECHARGE`
- **CHANNELNAME**: `B2BKIOSK`, `DMS`, `IPHONE`, `KIOSK`, `WEB`
- **CONTRACT_CATEGORY**: `INDIVIDUAL`, `Individual Premium`
- **DENOMINATION**: `1.5`, `10`, `2`, `5`, `Others`
- **ITEM_CODE**: `EV02`, `EV03`, `EV05`, `EV06`, `EV1.5`, `EV10`, `EV20`, `EV25`, `EVI05`, `RC1.5`, `RCQ02`, `RCQ03`, `RCQ05`, `RCQ06`, `RCQ1.5`, `RCQ10`, `RCQ20`, `RCQ25`
- **ITEM_NO**: `202507070010060213`, `202507070010060214`, `202602010050001049`, `202602050010005435`, `202602050010005484`, `202602050010006898`
- **NATIONALITY**: `BGD`, `EGY`, `IND`, `KWT`, `NPL`, `PHL`, `SDN`, `SYR`
- **OPERATEDBY**: `0`, `1025`
- **PREPOST_PAID**: `POST`, `PREP`
- **RECHARGE_SUB_TYPE**: `Digital-App`, `Digital-Dealer`, `Digital-Kiosk`, `Digital-Web`
- **RECHARGE_TYPE**: `Digital`
- **SERIAL_NUMBER**: `202507070010060213`, `202507070010060214`, `202602010050001049`, `202602050010005435`, `202602050010005484`, `202602050010006898`
- **SUBSCRIBERID**: `100494002306429345`, `103004002306427842`, `104584002306293509`, `104584002306315497`, `11565191`, `16284351066679`, `2251910`, `2624582`, `55151101173202`, `55155630626202`, `55192072635202`, `55195230014202`, `55342359052020`, `55342410112020`, `55588779812020`, `55914520130202`, `55918878969202`, `PR16765389`, `PR9487554`
- **THIRDPARTYNUMBER**: `51066679`, `51358097`, `51784013`, `55895769`, `99270184`
- **TRADETYPE**: `0`, `1102`, `1103`, `1108`, `1109`, `1112`, `1113`, `2`, `5`, `6`, `7`, `900`
- **VOUCHER_TYPE**: `E-Voucher`, `Electronic Top-Up`, `OTHER`, `Other Recharge`, `Physical Voucher`

<!-- ARIA:ENUM-VALUES-END -->
