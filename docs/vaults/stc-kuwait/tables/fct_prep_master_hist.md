---
table: FCT_PREP_MASTER_HIST
database: oracle
workspace: stc-kuwait
keywords: [360 view, account, acquisition, activation, balance, bandwidth, batch, billing, bundle, call, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, historical, history, income, international, internet, lifecycle, master, message, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, recharge, revenue, roaming, service, sms, snapshot, state, status, subscriber, subscription, tariff, temporal, time, time series, topup, touchpoint, travel, usage, voice]
description: "Fact table containing transactional/event data for Prep Master Hist"
row_count: 55079783
generated_at: 2026-07-01T22:24:18.303413+00:00
---

# FCT_PREP_MASTER_HIST

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| SNAPSHOT_DATE | DATE | ✗ |  | Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih. |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| NEXT_APPDATE | DATE | ✓ |  | Next Appdate |
| ID_NO | VARCHAR2 | ✓ |  | Müşterinin kimlik numarası (residence, pasaport vb.). |
| ID_TYPE | VARCHAR2 | ✓ |  | ID_NO da yer alan tanımlayıcının kategorik tipi. |
| ICC_NUMBER | VARCHAR2 | ✓ |  | SIM kartın fiziksel seri numarası (Integrated Circuit Card ID). |
| IMSI_NUMBER | VARCHAR2 | ✓ |  | Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara. |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). |
| CONTRACT_CATEGORY_GROUP | VARCHAR2 | ✓ |  | Contract Category Group |
| CATEGORY_TYPE | VARCHAR2 | ✓ |  | Category Type |
| NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). |
| NATIONALITY_LANG | VARCHAR2 | ✓ |  | Nationality Lang |
| NATIONALITY_GROUP | VARCHAR2 | ✓ |  | Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri). |
| NATIONALITY_SUB_GROUP | VARCHAR2 | ✓ |  | Uyruk alt grubu (daha detaylı sınıflandırma). |
| BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. |
| BS_FLAG | VARCHAR2 | ✓ |  | Bs Flag |
| NUM_TYPE | VARCHAR2 | ✓ |  | Num Type |
| RETAILER | VARCHAR2 | ✓ |  | Retailer |
| REGION | VARCHAR2 | ✓ |  | Geographic region |
| MNP_SUB | VARCHAR2 | ✓ |  | Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı. |
| CREDIT_RISK_PROFILE | VARCHAR2 | ✓ |  | Müşterinin kredi risk profili (düşük/orta/yüksek risk). |
| PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace). |
| MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Main Plan Prod Offering Id |
| MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | Main Plan Name |
| MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | Main Plan Equipid |
| MAIN_PLAN_RENTAL | VARCHAR2 | ✓ |  | Main Plan Rental |
| MAIN_PLAN_START_DATE | DATE | ✓ |  | Main Plan Start Date |
| PREP_BAL_AT_MONTH_START | NUMBER | ✓ |  | Prep Bal At Month Start |
| PREP_BAL_AT_PREV_MONTH_START | NUMBER | ✓ |  | Prep Bal At Prev Month Start |
| PREP_BAL_AS_OF_TODAY | NUMBER | ✓ |  | Prep Bal As Of Today |
| LT_LAST_ACTIVITY_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_DATA_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_VOICE_OUTGOING_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_VOICE_INCOMING_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_SMS_OUTGOING_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_RECHARGE_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_ROAMING_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_REVENUE_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_SGWCDR_ACTIVITY_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_PAID_SUBSCRIPTION_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_BUNDLE_PR_ID | VARCHAR2 | ✓ |  | Lt Last Bundle Pr Id |
| LT_LAST_BUNDLE_OFFER_ID | VARCHAR2 | ✓ |  | Lt Last Bundle Offer Id |
| LT_LAST_BUNDLE_OFFER_NAME | VARCHAR2 | ✓ |  | Lt Last Bundle Offer Name |
| LT_LAST_BUNDLE_VALIDIY | VARCHAR2 | ✓ |  | Lt Last Bundle Validiy |
| LT_LAST_BUNDLE_PRICE | VARCHAR2 | ✓ |  | Lt Last Bundle Price |
| LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Lt Last Bundle Actv Channel |
| LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | Lt Last Bundle Triggermode |
| LT_LAST_BUNDLE_TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Lt Last Bundle Transaction Type |
| LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Lt Last Bundle Prov Date |
| LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Lt Last Bundle Cycleendtime |
| LT_LAST_BUNDLE_ELAPSECYCLES | VARCHAR2 | ✓ |  | Lt Last Bundle Elapsecycles |
| LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB | NUMBER | ✓ |  | Data volume in MB |
| LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | Data volume in MB |
| LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Data volume in MB |
| LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_VOICE_ALL_NET_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_ROAMING_VOICE_MIN | NUMBER | ✓ |  | Duration in minutes |
| LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Count metric |
| ACTV_ADDONS | VARCHAR2 | ✓ |  | Actv Addons |
| ACTV_BONUS | VARCHAR2 | ✓ |  | Actv Bonus |
| ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Actv Vasservices |
| ACTV_BOOSTERS | VARCHAR2 | ✓ |  | Actv Boosters |
| ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Actv Roamingbundles |
| ACTV_ENABLERS | VARCHAR2 | ✓ |  | Actv Enablers |
| ACTV_BUNDLES | VARCHAR2 | ✓ |  | Actv Bundles |
| ACTV_LOYALTYCATALOG | VARCHAR2 | ✓ |  | Actv Loyaltycatalog |
| ACTV_FREEBIES | VARCHAR2 | ✓ |  | Actv Freebies |
| ACTV_MAINPLAN | VARCHAR2 | ✓ |  | Actv Mainplan |
| L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L1D Is Revenue Active Base |
| L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L7D Is Revenue Active Base |
| L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L15D Is Revenue Active Base |
| L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L30D Is Revenue Active Base |
| L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L90D Is Revenue Active Base |
| L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L120D Is Revenue Active Base |
| MTD_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Mtd Is Revenue Active Base |
| L1D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L1D Is Active Base |
| L7D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L7D Is Active Base |
| L15D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L15D Is Active Base |
| L30D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L30D Is Active Base |
| L90D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L90D Is Active Base |
| L120D_IS_ACTIVE_BASE | NUMBER | ✓ |  | L120D Is Active Base |
| L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L1D Activity Sources |
| L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L7D Activity Sources |
| L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L15D Activity Sources |
| L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L30D Activity Sources |
| L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L90D Activity Sources |
| L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L120D Activity Sources |
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  | Activity Status |
| PREPAID_BASE_TYPE | VARCHAR2 | ✓ |  | Prepaid Base Type |
| PREPAID_BASE_ROTATION | VARCHAR2 | ✓ |  | Prepaid Base Rotation |
| N1M_ACTIVITY_STATUS | VARCHAR2 | ✓ |  | N1M Activity Status |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.304027+00:00*

- **ACTIVITY_STATUS**: `CHURN_WITHIN_MONTH`, `CONNECTED`, `CONTRACT_TRANSFER`, `DISCONNECTED`, `FIRST_CONNECTED`, `GROSS_ADD`, `L2M_DISCONNECTED`, `POST_TO_PREP`, `PREP_TO_POST`, `RECONNECTED`
- **ACTV_ENABLERS**: `Camera Access Enabler`, `MBB Enable Calls`, `MBB Enable Calls | Prepaid 5G Quarterly 5KD`, `Prepaid 5G Monthly 1KD`, `Prepaid 5G Monthly 3KD`, `Prepaid 5G Quarterly 5KD`
- **ACTV_FREEBIES**: `Anghami prepaid Flag`, `Anghami prepaid Flag | terminated`
- **ACTV_MAINPLAN**: `Prepaid Mobile Package 65 USD`, `go net 12KD 3months`
- **ACTV_VASSERVICES**: `Multi-SIM Service`, `Multi-SIM Service | Prepaid Entertainment Menu`, `Multi-SIM Service | Prepaid Entertainment Menu | STC TV Prepaid Promo`, `Prepaid Entertainment Menu`, `Prepaid Entertainment Menu | STC TV Prepaid Promo`, `Prepaid Entertainment Menu | STC TV Prepaid Promo | stc TV Prepaid Promo`, `Prepaid Entertainment Menu | STC TV Prepaid Promo | stc TV Prepaid Promo | stc tv subscription`, `Prepaid Entertainment Menu | STC TV Prepaid Promo | stc TV Prepaid Service`, `Prepaid Entertainment Menu | STC TV Prepaid Promo | stc tv subscription`, `Prepaid Entertainment Menu | stc TV Prepaid Promo`, `Prepaid Entertainment Menu | stc TV Prepaid Promo | stc TV Prepaid Service`, `Prepaid Entertainment Menu | stc TV Prepaid Promo | stc tv subscription`, `Prepaid Entertainment Menu | stc TV Prepaid Service`, `Prepaid Entertainment Menu | stc TV Prepaid Service | stc tv subscription`, `Prepaid Entertainment Menu | stc tv subscription`, `STC TV Prepaid Promo`, `STC TV Prepaid Promo | stc tv subscription`, `stc TV Prepaid Service`, `stc TV Prepaid Service | stc tv subscription`, `stc tv subscription`
- **BS_FLAG**: `MAIN`
- **BS_TYPE**: `DATA`, `FIBER`, `VOICE`
- **CATEGORY_TYPE**: `B2B`, `B2C`, `EMP`, `TEST`
- **CONTRACT_CATEGORY_GROUP**: `CMM`, `CPI`, `CRP`, `CRV`, `Employee`, `Fixed CRPL`, `Fixed CRPS`, `Fixed CRV`, `HVC`, `HVU`, `ING`, `INP`, `INP Plus`, `INY`, `Others`, `TEST`, `VIP`, `VND`
- **CREDIT_RISK_PROFILE**: `GRAY`, `HIGH`, `LOW`, `MEDIUM`, `NO RISK`, `notfound`
- **ID_TYPE**: ``, `A`, `C`, `D`, `E`, `G`, `P`, `R`, `X`
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: `3PP`, `CHATBOT`, `CMS`, `DCLM`, `DCLMBULK`, `DMPOS`, `ESTORAPP`, `ESTORAPPNEW`, `ESTORWEB`, `ESTORWEBNEW`, `IVR`, `MOBAPP`, `SMS`, `SPPOS`, `TABS`, `WEB`
- **LT_LAST_BUNDLE_PRICE**: `0`, `0.2`, `0.34`, `0.5`, `1`, `10`, `108`, `11`, `12`, `12.75`, `13`, `144`, `15`, `15.3`, `151.2`, `16`, `18`, `19`, `2`, `2.5`, `20`, `21`, `22`, `22.95`, `24`, `25.2`, `3`, `3.5`, `30.6`, `36`, `37.8`, `38.25`, `4`, `4.5`, `43.2`, `5`, `50.4`, `51`, `6`, `63`, `64.8`, `7`, `7.5`, `8`, `84`, `9`
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: `AUTO_RENEWAL`, `AUTO_RENEWAL|DEALER`, `AUTO_RENEWAL|DEALER_USSD`, `AUTO_RENEWAL|DEALER_USSD|SMART_PAYMENT`, `AUTO_RENEWAL|DEALER_USSD|USER_USSD`, `AUTO_RENEWAL|SMART_PAYMENT`, `AUTO_RENEWAL|USER`, `AUTO_RENEWAL|USER_USSD`, `DEALER_USSD`, `DEALER_USSD|SMART_PAYMENT`, `DEALER_USSD|SMART_PAYMENT|USER_USSD`, `DEALER|SMART_PAYMENT`, `SMART_PAYMENT`, `SMART_PAYMENT|USER`, `SMART_PAYMENT|USER_USSD`, `USER`
- **LT_LAST_BUNDLE_TRIGGERMODE**: `0`, `1`, `2`, `3`, `4`, `7`, `8`, `D`, `F`
- **LT_LAST_BUNDLE_VALIDIY**: `1`, `15`, `180`, `20`, `28`, `30`, `365`, `5`, `60`, `7`, `90`
- **MAIN_PLAN_RENTAL**: `0`, `1.5`, `10`, `100`, `11`, `12`, `15`, `16`, `18`, `19`, `2`, `20`, `22`, `25`, `3`, `35`, `4`, `45`, `5`, `5.484`, `50`, `6`, `7`, `7.5`, `75`, `8`, `9`
- **MNP_SUB**: `N`, `Y`
- **N1M_ACTIVITY_STATUS**: `CHURN_WITHIN_MONTH`, `CONNECTED`, `CONTRACT_TRANSFER`, `DISCONNECTED`, `GROSS_ADD`, `L2M_DISCONNECTED`, `POST_TO_PREP`, `PREP_TO_POST`, `RECONNECTED`
- **NATIONALITY_GROUP**: `Expat`, `Local`
- **NATIONALITY_SUB_GROUP**: `Asian Expat`, `GCC Expat`, `Kuwaiti`, `Non GCC Arab Expat`, `Non-Kuwaiti`, `Other Expat`, `Western Expat`
- **NUM_TYPE**: `1`, `2`, `3`, `4`, `5`, `B`, `G`, `H`, `P`, `S`, `V`
- **PREPAID_BASE_ROTATION**: `PORT_IN`, `PORT_OUT`
- **PREPAID_BASE_TYPE**: `ArchivedChurn`, `Churn`, `Existing`, `NewEnrollment`, `ReversedNewEnrollment`
- **PREPAID_STATE_GROUP**: `ACTIVE`, `CHURN_WITHIN_MONTH`, `DISABLE`, `GRACE`, `HISTORICAL_CHURN`, `IDLE`, `POOL`, `PREP_TO_POST`
- **PREPOST_PAID**: `POST`, `PREP`
- **REGION**: `AJH`, `AMD`, `ASM`, `FRW`, `HWL`, `KWT`, `MBK`

<!-- ARIA:ENUM-VALUES-END -->
