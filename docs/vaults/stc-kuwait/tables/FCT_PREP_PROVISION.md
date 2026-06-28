---
table: FCT_PREP_PROVISION
database: oracle
workspace: stc-kuwait
keywords: [activation, membership, opt-in, package pickup, paket alımı, prepaid, provision,
  subscription, üyelik]
generated_at: '2026-06-16T03:23:43.169377+00:00'
enriched_at: '2026-06-16T14:59:52.299288+00:00'
description: Fact table that records package, tariff or service membership (provisioning),
  activation and cancellation transactions of prepaid subscribers.
---

# FCT_PREP_PROVISION

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
 | PROD_OFFERING_ID | VARCHAR2 | ✓ |  | If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group. | 
 | PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle' | 
 | PRODUCT_TYPE | VARCHAR2 | ✓ |  | Stores the categorization of product groups such as AddOn, Bundle, Device. | 
 | OFFER_ID | NUMBER | ✓ |  | The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID. | 
 | PR_ID | NUMBER | ✓ |  | Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI. | 
 | SERVICETYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | EQUIPID | VARCHAR2 | ✓ |  | Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52. | 
 | LOGDATE | DATE | ✓ |  | Date/time stamp when the log record was created | 
 | ORDERSTATUS | VARCHAR2 | ✓ |  | Order/transaction status (successful, failed, pending, cancelled, etc.) | 
 | TRIGGERMODE | VARCHAR2 | ✓ |  | How the action is triggered (manual, automatic, campaign, system triggered, etc.) | 
 | SOURCE_FLAG | VARCHAR2 | ✓ |  | The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily. | 
 | BILLCYCLEID | VARCHAR2 | ✓ |  | The billing cycle ID gives the type of cycle in months, in date format. | 
 | CYCLETYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | CYCLELENGTH | NUMBER | ✓ |  | Cycle length (e.g. 30 days, 7 days) | 
 | ELAPSECYCLES | NUMBER | ✓ |  | Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time. | 
 | TOTALCYCLES | NUMBER | ✓ |  | It should not be used unnecessarily. | 
 | CYCLEBEGINTIME | DATE | ✓ |  | Start time of the current cycle | 
 | CYCLEENDTIME | DATE | ✓ |  | End time of the current cycle | 
 | INNERCYCLEBEGINTIME | DATE | ✓ |  | It should not be used unnecessarily. | 
 | INNERCYCLEENDTIME | DATE | ✓ |  | It should not be used unnecessarily. | 
 | BILLAMOUNT | NUMBER | ✓ |  | It indicates the amount of KD withdrawn from the user in return for the provision. | 
 | PAYTYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | PREPAIDBALANCE | NUMBER | ✓ |  | Prepaid balance amount at the time of transaction | 
 | RELIED_ON_PRID | VARCHAR2 | ✓ |  | PR_ID (reference package) of the connected product (Main plan) | 
 | RELIED_SERVICE_START_DATE | DATE | ✓ |  | Start date of the connected service (Main plan) | 
 | RELIED_SERVICE_END_DATE | DATE | ✓ |  | End date of the connected service (Main plan) | 
 | RELIED_EQUIPID | VARCHAR2 | ✓ |  | EQUIPID of the dependent product (Master plan). | 
 | RELIED_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Product offering ID of the connected product (Main plan) | 
 | RELIED_OFFER_ID | VARCHAR2 | ✓ |  | Offer ID of the connected product (Main plan) | 
 | RELIED_PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Name of the linked product (Main plan) | 
 | RELIED_RENTAL | NUMBER | ✓ |  | It indicates the amount of KD withdrawn from the user in return for the provision of the connected product. | 
 | CDR_PRODUCTSERIAL | VARCHAR2 | ✓ |  | Product serial number in the CDR record — used to match the transaction to the CDR | 
 | CDR_SERIALNO | VARCHAR2 | ✓ |  | CDR serial number — unique tracking number of the usage record | 
 | CHANNEL_NAME | VARCHAR2 | ✓ |  | Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.) | 
 | ACCOUNTTYPE_REF_COMBINATION | VARCHAR2 | ✓ |  | Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations) | 
 | TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT | AUTO_PAYMENT gibi | Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT | AUTO_PAYMENT gibi | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​​​​separated by , since there can be more than one provision type at the same time. | 

## Keywords

## Business Metadata

**Description:** Fact table that records package, tariff or service membership (provisioning), activation and cancellation transactions of prepaid subscribers.

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

Counts **unique subscribers** (`COUNT(DISTINCT SUBNO)`) per bundle (`PRODUCT_OFFER_NAME`) for the
last 30 days against the prior 30 days, plus the `delta` between them. Always filter
`PRODUCT_TYPE = 'Bundles'` (the live enum is plural — "Bundles", not "Bundle") and use `LOGDATE`
as the provisioning event date. Count **distinct `SUBNO`**, not rows, so repeated provisioning
records for the same line don't inflate the totals. A positive `delta` means the bundle gained
subscribers month-over-month.

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

Daily count of **distinct subscribers** who provisioned a bundle over the last 30 days — one row
per day. Use it to spot day-level spikes/dips in bundle uptake. `TRUNC(LOGDATE)` buckets by day,
`COUNT(DISTINCT SUBNO)` counts unique lines (not provisioning rows), and `PRODUCT_TYPE = 'Bundles'`
restricts to bundle products.

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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​​​separated by , since there can be more than one provision type at the same time.
