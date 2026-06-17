---
table: FCT_PREP_MASTER_HIST
database: oracle
workspace: stc-kuwait
keywords: [archive, arşiv, history, master, prepaid, tarihçe]
generated_at: '2026-06-16T03:23:43.169154+00:00'
enriched_at: '2026-06-16T14:59:52.297842+00:00'
description: History data table that contains historical (archived) records of the
  Prepaid master table.
---

# FCT_PREP_MASTER_HIST

**Description:** No description provided yet.

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
| MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  |  |
| MAIN_PLAN_NAME | VARCHAR2 | ✓ |  |  |
| MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  |  |
| MAIN_PLAN_RENTAL | NUMBER | ✓ |  |  |
| MAIN_PLAN_START_DATE | DATE | ✓ |  |  |
| PREP_BAL_AT_MONTH_START | VARCHAR2 | ✓ |  |  |
| PREP_BAL_AT_PREV_MONTH_START | VARCHAR2 | ✓ |  |  |
| PREP_BAL_AS_OF_TODAY | VARCHAR2 | ✓ |  |  |
| LT_LAST_ACTIVITY_DT | DATE | ✓ |  |  |
| LT_LAST_DATA_DT | DATE | ✓ |  |  |
| LT_LAST_VOICE_OUTGOING_DT | DATE | ✓ |  |  |
| LT_LAST_VOICE_INCOMING_DT | DATE | ✓ |  |  |
| LT_LAST_SMS_OUTGOING_DT | DATE | ✓ |  |  |
| LT_LAST_RECHARGE_DT | DATE | ✓ |  |  |
| LT_LAST_ROAMING_DT | DATE | ✓ |  |  |
| LT_LAST_REVENUE_DT | DATE | ✓ |  |  |
| LT_LAST_SGWCDR_ACTIVITY_DT | DATE | ✓ |  |  |
| LT_LAST_PAID_SUBSCRIPTION_DT | DATE | ✓ |  |  |
| LT_LAST_BUNDLE_PR_ID | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_OFFER_ID | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_OFFER_NAME | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VALIDIY | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_PRICE | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_TRANSACTION_TYP | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  |  |
| LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  |  |
| LT_LAST_BUNDLE_ELAPSECYCLES | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  |  |
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_LOCAL_ONN | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFF | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_ALL_NET_M | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_INTERNATI | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_ONNET_DURA | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_OFFNET_DUR | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_INTERCALL_ | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_ROAMING_VOICE_M | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  |  |
| LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  |  |
| ACTV_ADDONS | VARCHAR2 | ✓ |  |  |
| ACTV_OFFERS | VARCHAR2 | ✓ |  |  |
| ACTV_FREEBIES | VARCHAR2 | ✓ |  |  |
| ACTV_DISCOUNTOFFERS | VARCHAR2 | ✓ |  |  |
| ACTV_VASSERVICES | VARCHAR2 | ✓ |  |  |
| ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  |  |
| ACTV_BUNDLES | VARCHAR2 | ✓ |  |  |
| ACTV_ROAMINGPAYGO | VARCHAR2 | ✓ |  |  |
| ACTV_ROAMING_ACCESS | VARCHAR2 | ✓ |  |  |
| ACTV_ROAMINGLANDINGPAGE | VARCHAR2 | ✓ |  |  |
| L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  |  |
| L1D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L7D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L15D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L30D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L90D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L120D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  |  |
| L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  |  |
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  |  |

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **SNAPSHOT_DATE**: 
- **CONTRNO**: 
- **SUBNO**: 
- **PREPOST_PAID**: 
- **APPDATE**: 
- **NEXT_APPDATE**: 
- **ID_NO**: 
- **ID_TYPE**: 
- **ICC_NUMBER**: 
- **IMSI_NUMBER**: 
- **CONTRACT_CATEGORY**: 
- **CONTRACT_CATEGORY_GROUP**: 
- **CATEGORY_TYPE**: 
- **NATIONALITY**: 
- **NATIONALITY_LANG**: 
- **NATIONALITY_GROUP**: 
- **NATIONALITY_SUB_GROUP**: 
- **BS_TYPE**: 
- **BS_FLAG**: 
- **NUM_TYPE**: 
- **RETAILER**: 
- **REGION**: 
- **MNP_SUB**: 
- **CREDIT_RISK_PROFILE**: 
- **PREPAID_STATE_GROUP**: 
- **MAIN_PLAN_PROD_OFFERING_ID**: 
- **MAIN_PLAN_NAME**: 
- **MAIN_PLAN_EQUIPID**: 
- **MAIN_PLAN_RENTAL**: 
- **MAIN_PLAN_START_DATE**: 
- **PREP_BAL_AT_MONTH_START**: 
- **PREP_BAL_AT_PREV_MONTH_START**: 
- **PREP_BAL_AS_OF_TODAY**: 
- **LT_LAST_ACTIVITY_DT**: 
- **LT_LAST_DATA_DT**: 
- **LT_LAST_VOICE_OUTGOING_DT**: 
- **LT_LAST_VOICE_INCOMING_DT**: 
- **LT_LAST_SMS_OUTGOING_DT**: 
- **LT_LAST_RECHARGE_DT**: 
- **LT_LAST_ROAMING_DT**: 
- **LT_LAST_REVENUE_DT**: 
- **LT_LAST_SGWCDR_ACTIVITY_DT**: 
- **LT_LAST_PAID_SUBSCRIPTION_DT**: 
- **LT_LAST_BUNDLE_PR_ID**: 
- **LT_LAST_BUNDLE_OFFER_ID**: 
- **LT_LAST_BUNDLE_OFFER_NAME**: 
- **LT_LAST_BUNDLE_VALIDIY**: 
- **LT_LAST_BUNDLE_PRICE**: 
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: 
- **LT_LAST_BUNDLE_TRIGGERMODE**: 
- **LT_LAST_BUNDLE_TRANSACTION_TYP**: 
- **LT_LAST_BUNDLE_PROV_DATE**: 
- **LT_LAST_BUNDLE_CYCLEENDTIME**: 
- **LT_LAST_BUNDLE_ELAPSECYCLES**: 
- **LT_LAST_BUNDLE_TERMINATION_DT**: 
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL**: 
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: 
- **LT_LAST_BUNDLE_FREE_DATA_MB**: 
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONN**: 
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFF**: 
- **LT_LAST_BUNDLE_VOICE_ALL_NET_M**: 
- **LT_LAST_BUNDLE_VOICE_INTERNATI**: 
- **LT_LAST_BUNDLE_FREE_ONNET_DURA**: 
- **LT_LAST_BUNDLE_FREE_OFFNET_DUR**: 
- **LT_LAST_BUNDLE_FREE_INTERCALL_**: 
- **LT_LAST_BUNDLE_ROAMING_VOICE_M**: 
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: 
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: 
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: 
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: 
- **ACTV_ADDONS**: 
- **ACTV_OFFERS**: 
- **ACTV_FREEBIES**: 
- **ACTV_DISCOUNTOFFERS**: 
- **ACTV_VASSERVICES**: 
- **ACTV_ROAMINGBUNDLES**: 
- **ACTV_BUNDLES**: 
- **ACTV_ROAMINGPAYGO**: 
- **ACTV_ROAMING_ACCESS**: 
- **ACTV_ROAMINGLANDINGPAGE**: 
- **L1D_IS_REVENUE_ACTIVE_BASE**: 
- **L7D_IS_REVENUE_ACTIVE_BASE**: 
- **L15D_IS_REVENUE_ACTIVE_BASE**: 
- **L30D_IS_REVENUE_ACTIVE_BASE**: 
- **L90D_IS_REVENUE_ACTIVE_BASE**: 
- **L120D_IS_REVENUE_ACTIVE_BASE**: 
- **L1D_IS_ACTIVE_BASE**: 
- **L7D_IS_ACTIVE_BASE**: 
- **L15D_IS_ACTIVE_BASE**: 
- **L30D_IS_ACTIVE_BASE**: 
- **L90D_IS_ACTIVE_BASE**: 
- **L120D_IS_ACTIVE_BASE**: 
- **L1D_ACTIVITY_SOURCES**: 
- **L7D_ACTIVITY_SOURCES**: 
- **L15D_ACTIVITY_SOURCES**: 
- **L30D_ACTIVITY_SOURCES**: 
- **L90D_ACTIVITY_SOURCES**: 
- **L120D_ACTIVITY_SOURCES**: 
- **ACTIVITY_STATUS**:
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **SNAPSHOT_DATE**: Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih.
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **ID_NO**: Müşterinin kimlik numarası (residence, pasaport vb.).
- **ID_TYPE**: ID_NO da yer alan tanımlayıcının kategorik tipi.
- **ICC_NUMBER**: SIM kartın fiziksel seri numarası (Integrated Circuit Card ID).
- **IMSI_NUMBER**: Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **NATIONALITY_GROUP**: Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri).
- **NATIONALITY_SUB_GROUP**: Uyruk alt grubu (daha detaylı sınıflandırma).
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **MNP_SUB**: Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı.
- **CREDIT_RISK_PROFILE**: Müşterinin kredi risk profili (düşük/orta/yüksek risk).
- **PREPAID_STATE_GROUP**: Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace).
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **SNAPSHOT_DATE**: Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih.
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **ID_NO**: Müşterinin kimlik numarası (residence, pasaport vb.).
- **ID_TYPE**: ID_NO da yer alan tanımlayıcının kategorik tipi.
- **ICC_NUMBER**: SIM kartın fiziksel seri numarası (Integrated Circuit Card ID).
- **IMSI_NUMBER**: Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **NATIONALITY_GROUP**: Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri).
- **NATIONALITY_SUB_GROUP**: Uyruk alt grubu (daha detaylı sınıflandırma).
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **MNP_SUB**: Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı.
- **CREDIT_RISK_PROFILE**: Müşterinin kredi risk profili (düşük/orta/yüksek risk).
- **PREPAID_STATE_GROUP**: Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace).
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
## Business Metadata

**Description:** History data table that contains historical (archived) records of the Prepaid master table.

### Column Descriptions

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
