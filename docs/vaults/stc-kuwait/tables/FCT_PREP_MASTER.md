---
table: FCT_PREP_MASTER
database: oracle
workspace: stc-kuwait
keywords: [bakiye, balance, fact, kpi, master, prepaid, snapshot, summary, özet]
generated_at: '2026-06-16T03:23:43.168994+00:00'
enriched_at: '2026-06-28T11:01:41.751824+00:00'
description: Main fact table that keeps basic metrics, balance, usage and general
  transaction summaries of Prepaid subscribers on a daily basis.
---

# FCT_PREP_MASTER

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | SNAPSHOT_DATE | DATE | ✓ |  | The date on which the data represents the snapshot of the day. | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
| NEXT_APPDATE | DATE | ✓ |  |  |
 | ID_NO | VARCHAR2 | ✓ |  | Customer's identification number (residence, passport, etc.). | 
 | ID_TYPE | VARCHAR2 | ✓ |  | The categorical type of the identifier contained in ID_NO. | 
 | ICC_NUMBER | VARCHAR2 | ✓ |  | Physical serial number of the SIM card (Integrated Circuit Card ID). | 
 | IMSI_NUMBER | VARCHAR2 | ✓ |  | International Mobile Subscriber Identity. The number that identifies the subscriber in the network. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
| CONTRACT_CATEGORY_GROUP | VARCHAR2 | ✓ |  |  |
| CATEGORY_TYPE | VARCHAR2 | ✓ |  |  |
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
| NATIONALITY_LANG | VARCHAR2 | ✓ |  |  |
 | NATIONALITY_GROUP | VARCHAR2 | ✓ |  | Nationality major group (e.g. Local / Foreign / Gulf countries). | 
 | NATIONALITY_SUB_GROUP | VARCHAR2 | ✓ |  | Nationality subgroup (more detailed classification). | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
| BS_FLAG | VARCHAR2 | ✓ |  |  |
| NUM_TYPE | VARCHAR2 | ✓ |  |  |
| RETAILER | VARCHAR2 | ✓ |  |  |
| REGION | VARCHAR2 | ✓ |  |  |
 | MNP_SUB | VARCHAR2 | ✓ |  | Flag of whether there is a subscriber coming with number portability (Mobile Number Portability). | 
 | CREDIT_RISK_PROFILE | VARCHAR2 | ✓ |  | Customer's credit risk profile (low/medium/high risk). | 
 | PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Lifecycle status group of the prepaid line (Active, Disable, Grace). | 
 | MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_RENTAL | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_START_DATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | PREP_BAL_AT_MONTH_START | VARCHAR2 | ✓ |  | Prepaid balance amount at the beginning of the current month | 
 | PREP_BAL_AT_PREV_MONTH_START | VARCHAR2 | ✓ |  | Current prepaid balance amount as of today | 
 | PREP_BAL_AS_OF_TODAY | VARCHAR2 | ✓ |  | Current prepaid balance amount as of today | 
 | LT_LAST_ACTIVITY_DT | DATE | ✓ |  | Date of any recent activity on the line | 
 | LT_LAST_DATA_DT | DATE | ✓ |  | Last mobile data (internet) usage date | 
 | LT_LAST_VOICE_OUTGOING_DT | DATE | ✓ |  | Last outgoing voice call date | 
 | LT_LAST_VOICE_INCOMING_DT | DATE | ✓ |  | Last incoming voice call date | 
 | LT_LAST_SMS_OUTGOING_DT | DATE | ✓ |  | Last sent SMS date | 
 | LT_LAST_RECHARGE_DT | DATE | ✓ |  | Last TL top-up (top-up/balance top-up) date | 
 | LT_LAST_ROAMING_DT | DATE | ✓ |  | Last international roaming usage date | 
 | LT_LAST_REVENUE_DT | DATE | ✓ |  | Date of the last transaction that generated income for STC | 
 | LT_LAST_SGWCDR_ACTIVITY_DT | DATE | ✓ |  | Last data activity date according to SGW (Serving Gateway) CDR records (data session based) | 
 | LT_LAST_PAID_SUBSCRIPTION_DT | DATE | ✓ |  | Last paid subscription/package purchase date | 
 | LT_LAST_BUNDLE_PR_ID | VARCHAR2 | ✓ |  | Product ID of the last package received | 
 | LT_LAST_BUNDLE_OFFER_ID | VARCHAR2 | ✓ |  | Offer ID of the last package purchased | 
 | LT_LAST_BUNDLE_OFFER_NAME | VARCHAR2 | ✓ |  | Name of the last package received | 
 | LT_LAST_BUNDLE_VALIDIY | VARCHAR2 | ✓ |  | Validity period of the last package purchased | 
 | LT_LAST_BUNDLE_PRICE | NUMBER | ✓ |  | Price of the last package purchased | 
 | LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.) | 
 | LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | How the package is triggered (manual, automatic renewal, campaign, etc.) | 
| LT_LAST_BUNDLE_TRANSACTION_TYP | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Provisioning date of the package to the system | 
 | LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Packet cycle end time | 
 | LT_LAST_BUNDLE_ELAPSECYCLES | NUMBER | ✓ |  | How many cycles/periods the package has been used | 
 | LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Package termination date | 
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | International (roaming) data quota (MB) of the package | 
 | LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Amount of free data included in the package (MB) | 
| LT_LAST_BUNDLE_VOICE_LOCAL_ONN | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFF | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_ALL_NET_M | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_INTERNATI | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_ONNET_DURA | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_OFFNET_DUR | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_INTERCALL_ | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_ROAMING_VOICE_M | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Number of domestic SMS | 
 | LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Total number of SMS to all networks | 
 | LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Number of international SMS | 
 | LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Number of SMS in international roaming | 
 | ACTV_ADDONS | VARCHAR2 | ✓ |  | Active additional package (add-on) services | 
 | ACTV_OFFERS | VARCHAR2 | ✓ |  | Active campaigns/offers | 
 | ACTV_FREEBIES | VARCHAR2 | ✓ |  | Active free/gift services | 
 | ACTV_DISCOUNTOFFERS | VARCHAR2 | ✓ |  | Active discount offers | 
 | ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Active value added services (VAS — Value Added Services; e.g. ringback tone, content services) | 
 | ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Active international roaming packages | 
 | ACTV_BUNDLES | VARCHAR2 | ✓ |  | Active main packages | 
 | ACTV_ROAMINGPAYGO | VARCHAR2 | ✓ |  | Active usage based (pay-as-you-go) roaming service | 
 | ACTV_ROAMING_ACCESS | VARCHAR2 | ✓ |  | On/off status of international roaming access | 
 | ACTV_ROAMINGLANDINGPAGE | VARCHAR2 | ✓ |  | Roaming landing page (information page that opens when you go abroad) service status | 
 | L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has there been any income generating activity in the last day? | 
 | L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has he had income-producing activity in the last 7 days? | 
 | L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has he had income-producing activity in the last 15 days? | 
 | L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have income-producing activity in the last 30 days? | 
 | L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have revenue-producing activity in the last 90 days? | 
 | L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have income-producing activity in the last 120 days? | 
 | L1D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last day? | 
 | L7D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 7 days? | 
 | L15D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 15 days? | 
 | L30D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 30 days? | 
 | L90D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 90 days? | 
 | L120D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 120 days? | 
 | L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources in the last day | 
 | L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources for the last 7 days | 
 | L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Sources of activity in the last 15 days | 
 | L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 30 days | 
 | L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 90 days | 
 | L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 120 days | 
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  |  |

## Keywords

## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Business Metadata

