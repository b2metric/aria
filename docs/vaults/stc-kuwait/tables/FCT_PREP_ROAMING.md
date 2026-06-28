---
table: FCT_PREP_ROAMING
database: oracle
workspace: stc-kuwait
keywords: [abroad, circulation, dolaşım, international, prepaid, roaming, travel,
  yurtdışı]
generated_at: '2026-06-16T03:23:43.170285+00:00'
enriched_at: '2026-06-28T03:12:44.797467+00:00'
description: Fact table that keeps data, voice and SMS usage details of prepaid subscribers
  in roaming networks.
---

# FCT_PREP_ROAMING

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
 | TRANSDATE | DATE | ✓ |  | Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs | 
 | IMEI | VARCHAR2 | ✓ |  | International Mobile Equipment Identity. | 
 | CALLTYPE | VARCHAR2 | ✓ |  | Type of call (e.g., voice, data). | 
 | CDR_CATEGORY | VARCHAR2 | ✓ |  | CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.) | 
| CHARGETYPE | VARCHAR2 | ✓ |  |  |
| INTL_FLAG | VARCHAR2 | ✓ |  |  |
| USED_NETWORK | VARCHAR2 | ✓ |  |  |
 | OFFER_ID | NUMBER | ✓ |  | Offer/campaign ID under which the transaction is applied | 
 | RENTAL_TYPE | NUMBER | ✓ |  | Type of rental service. | 
| CALLEDHOMECODE | VARCHAR2 | ✓ |  |  |
| CALLEDROAMCODE | VARCHAR2 | ✓ |  |  |
| CALLEDROAMHOMECODE | VARCHAR2 | ✓ |  |  |
| CALLINGHOMECODE | VARCHAR2 | ✓ |  |  |
| CALLINGROAMCODE | VARCHAR2 | ✓ |  |  |
| CALLINGROAMHOMECODE | VARCHAR2 | ✓ |  |  |
| CALLINGCELLID | VARCHAR2 | ✓ |  |  |
| CALLEDCELLID | VARCHAR2 | ✓ |  |  |
| TARIFFCLASS | VARCHAR2 | ✓ |  |  |
| TARIFF_GROUP | VARCHAR2 | ✓ |  |  |
| BILLTEXT | VARCHAR2 | ✓ |  |  |
 | BILLAMOUNT | NUMBER | ✓ |  | Net amount invoiced | 
| GROSS_AMOUNT | NUMBER | ✓ |  |  |
 | CHARGEDURATION | VARCHAR2 | ✓ |  | Time used, quantity or MB | 
| CALLDURATION | VARCHAR2 | ✓ |  |  |
| CDR_SERIALNO | VARCHAR2 | ✓ |  |  |
| CDR_SERIALNO_HASH | VARCHAR2 | ✓ |  |  |
 | OPERATOR | VARCHAR2 | ✓ |  | Name of the guest operator (the network to which the subscriber is connected while roaming) | 
 | COUNTRY | VARCHAR2 | ✓ |  | Name of guest country — roaming country | 
 | OPERATOR_CODE | VARCHAR2 | ✓ |  | Guest operator's code (usually MCC+MNC or internal reference code) | 
| CALLINGROAMINFO | VARCHAR2 | ✓ |  |  |
| CALLINGROAMDECIMALINFO | VARCHAR2 | ✓ |  |  |
| CALLEDROAMINFO | VARCHAR2 | ✓ |  |  |
| USAGESERVICETYPE | VARCHAR2 | ✓ |  |  |
| DWH_UPDATE_DATE | DATE | ✓ |  |  |
| CALLINGROAMCOUNTRYCODE | VARCHAR2 | ✓ |  |  |
| CALLINGROAMAREANUMBER | VARCHAR2 | ✓ |  |  |
| CALLINGROAMNETWORKCODE | VARCHAR2 | ✓ |  |  |
| LAST_ROAM_SIGNAL_COUNTRY | VARCHAR2 | ✓ |  |  |
| LAST_ROAM_SIGNAL_DT | DATE | ✓ |  |  |

## Keywords

## Business Metadata

## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CDR_CATEGORY**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **OFFER_ID**: Offer/campaign ID under which the transaction is applied
- **BILLAMOUNT**: Net amount invoiced
- **CHARGEDURATION**: Time used, quantity or MB
- **OPERATOR**: Name of the guest operator (the network to which the subscriber is connected while roaming)
- **COUNTRY**: Name of guest country — roaming country
- **OPERATOR_CODE**: Guest operator's code (usually MCC+MNC or internal reference code)

## Relationships

- `CONTRNO` → `FCT_PREP_MASTER.CONTRNO` (foreign_key)
