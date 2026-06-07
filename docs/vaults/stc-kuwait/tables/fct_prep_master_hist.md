---
table: FCT_PREP_MASTER_HIST
database: oracle
workspace: stc-kuwait
keywords: [360 view, account, acquisition, activation, balance, bandwidth, batch,
  billing, bundle, call, channel, contract, country, credit, customer, data, date,
  demographic, etl, financial, geography, historical, history, income, international,
  internet, lifecycle, master, message, minutes, mobile, money, msisdn, nationality,
  offer, package, payment, phone number, prepaid, product, provision, recharge, revenue,
  roaming, service, sms, snapshot, state, status, subscriber, subscription, tariff,
  temporal, time, time series, topup, touchpoint, travel, usage, voice]
generated_at: 2026-06-07 11:22:23.800307+00:00
enriched_at: '2026-06-07T11:22:24.330524+00:00'
---

# FCT_PREP_MASTER_HIST

**Description:** Fact table containing transactional/event data for Prep Master Hist

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | SNAPSHOT_DATE | DATE | ✓ |  | Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih. | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
| NEXT_APPDATE | DATE | ✓ |  | Next Appdate |
 | ID_NO | VARCHAR2 | ✓ |  | Müşterinin kimlik numarası (residence, pasaport vb.). | 
 | ID_TYPE | VARCHAR2 | ✓ |  | ID_NO da yer alan tanımlayıcının kategorik tipi. | 
 | ICC_NUMBER | VARCHAR2 | ✓ |  | SIM kartın fiziksel seri numarası (Integrated Circuit Card ID). | 
 | IMSI_NUMBER | VARCHAR2 | ✓ |  | Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanıml | 
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
| MAIN_PLAN_RENTAL | NUMBER | ✓ |  | Main Plan Rental |
| MAIN_PLAN_START_DATE | DATE | ✓ |  | Main Plan Start Date |
| PREP_BAL_AT_MONTH_START | VARCHAR2 | ✓ |  | Prep Bal At Month Start |
| PREP_BAL_AT_PREV_MONTH_START | VARCHAR2 | ✓ |  | Prep Bal At Prev Month Start |
| PREP_BAL_AS_OF_TODAY | VARCHAR2 | ✓ |  | Prep Bal As Of Today |
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
| LT_LAST_BUNDLE_PRICE | NUMBER | ✓ |  | Lt Last Bundle Price |
| LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Lt Last Bundle Actv Channel |
| LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | Lt Last Bundle Triggermode |
| LT_LAST_BUNDLE_TRANSACTION_TYP | VARCHAR2 | ✓ |  | Lt Last Bundle Transaction Typ |
| LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Lt Last Bundle Prov Date |
| LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Lt Last Bundle Cycleendtime |
| LT_LAST_BUNDLE_ELAPSECYCLES | NUMBER | ✓ |  | Lt Last Bundle Elapsecycles |
| LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Date/timestamp field |
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL | VARCHAR2 | ✓ |  | Lt Last Bundle Data Gprs Local |
| LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | Data volume in MB |
| LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Data volume in MB |
| LT_LAST_BUNDLE_VOICE_LOCAL_ONN | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Local Onn |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFF | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Local Off |
| LT_LAST_BUNDLE_VOICE_ALL_NET_M | VARCHAR2 | ✓ |  | Lt Last Bundle Voice All Net M |
| LT_LAST_BUNDLE_VOICE_INTERNATI | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Internati |
| LT_LAST_BUNDLE_FREE_ONNET_DURA | VARCHAR2 | ✓ |  | Lt Last Bundle Free Onnet Dura |
| LT_LAST_BUNDLE_FREE_OFFNET_DUR | VARCHAR2 | ✓ |  | Lt Last Bundle Free Offnet Dur |
| LT_LAST_BUNDLE_FREE_INTERCALL_ | VARCHAR2 | ✓ |  | Lt Last Bundle Free Intercall  |
| LT_LAST_BUNDLE_ROAMING_VOICE_M | VARCHAR2 | ✓ |  | Lt Last Bundle Roaming Voice M |
| LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Count metric |
| LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Count metric |
| ACTV_ADDONS | VARCHAR2 | ✓ |  | Actv Addons |
| ACTV_OFFERS | VARCHAR2 | ✓ |  | Actv Offers |
| ACTV_FREEBIES | VARCHAR2 | ✓ |  | Actv Freebies |
| ACTV_DISCOUNTOFFERS | VARCHAR2 | ✓ |  | Actv Discountoffers |
| ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Actv Vasservices |
| ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Actv Roamingbundles |
| ACTV_BUNDLES | VARCHAR2 | ✓ |  | Actv Bundles |
| ACTV_ROAMINGPAYGO | VARCHAR2 | ✓ |  | Actv Roamingpaygo |
| ACTV_ROAMING_ACCESS | VARCHAR2 | ✓ |  | Actv Roaming Access |
| ACTV_ROAMINGLANDINGPAGE | VARCHAR2 | ✓ |  | Actv Roaminglandingpage |
| L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L1D Is Revenue Active Base |
| L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L7D Is Revenue Active Base |
| L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L15D Is Revenue Active Base |
| L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L30D Is Revenue Active Base |
| L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L90D Is Revenue Active Base |
| L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | L120D Is Revenue Active Base |
| L1D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L1D Is Active Base |
| L7D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L7D Is Active Base |
| L15D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L15D Is Active Base |
| L30D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L30D Is Active Base |
| L90D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L90D Is Active Base |
| L120D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | L120D Is Active Base |
| L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L1D Activity Sources |
| L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L7D Activity Sources |
| L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L15D Activity Sources |
| L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L30D Activity Sources |
| L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L90D Activity Sources |
| L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | L120D Activity Sources |
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  | Activity Status |

## Keywords

360 view, account, acquisition, activation, balance, bandwidth, batch, billing, bundle, call, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, historical, history, income, international, internet, lifecycle, master, message, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, recharge, revenue, roaming, service, sms, snapshot, state, status, subscriber, subscription, tariff, temporal, time, time series, topup, touchpoint, travel, usage, voice
## Business Metadata


### Column Descriptions

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
