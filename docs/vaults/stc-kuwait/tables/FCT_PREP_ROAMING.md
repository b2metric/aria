---
table: FCT_PREP_ROAMING
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, bandwidth, batch, billing, bundle, call,
  channel, contract, country, customer, data, date, demographic, etl, financial, geography,
  income, international, internet, lifecycle, minutes, mobile, money, msisdn, nationality,
  offer, package, payment, phone number, prepaid, product, provision, revenue, roaming,
  service, snapshot, state, status, subscriber, subscription, tariff, temporal, time,
  touchpoint, travel, usage, voice]
generated_at: 2026-06-07 11:22:23.803544+00:00
enriched_at: '2026-06-07T11:22:24.336584+00:00'
---

# FCT_PREP_ROAMING

**Description:** Fact table containing transactional/event data for Prep Roaming

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. | 
 | TRANSDATE | DATE | ✓ |  | İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi | 
| IMEI | VARCHAR2 | ✓ |  | Imei |
| CALLTYPE | VARCHAR2 | ✓ |  | Calltype |
 | CDR_CATEGORY | VARCHAR2 | ✓ |  | CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS | 
| CHARGETYPE | VARCHAR2 | ✓ |  | Chargetype |
| INTL_FLAG | VARCHAR2 | ✓ |  | Intl Flag |
| USED_NETWORK | VARCHAR2 | ✓ |  | Used Network |
 | OFFER_ID | NUMBER | ✓ |  | İşlemin altında uygulandığı teklif/kampanya ID'si | 
| RENTAL_TYPE | NUMBER | ✓ |  | Rental Type |
| CALLEDHOMECODE | VARCHAR2 | ✓ |  | Calledhomecode |
| CALLEDROAMCODE | VARCHAR2 | ✓ |  | Calledroamcode |
| CALLEDROAMHOMECODE | VARCHAR2 | ✓ |  | Calledroamhomecode |
| CALLINGHOMECODE | VARCHAR2 | ✓ |  | Callinghomecode |
| CALLINGROAMCODE | VARCHAR2 | ✓ |  | Callingroamcode |
| CALLINGROAMHOMECODE | VARCHAR2 | ✓ |  | Callingroamhomecode |
| CALLINGCELLID | VARCHAR2 | ✓ |  | Callingcellid |
| CALLEDCELLID | VARCHAR2 | ✓ |  | Calledcellid |
| TARIFFCLASS | VARCHAR2 | ✓ |  | Tariffclass |
| TARIFF_GROUP | VARCHAR2 | ✓ |  | Tariff Group |
| BILLTEXT | VARCHAR2 | ✓ |  | Billtext |
 | BILLAMOUNT | NUMBER | ✓ |  | Faturalanan net tutar | 
| GROSS_AMOUNT | NUMBER | ✓ |  | Gross Amount |
 | CHARGEDURATION | VARCHAR2 | ✓ |  | Kullanılan süre, adet veyahut MB | 
| CALLDURATION | VARCHAR2 | ✓ |  | Callduration |
| CDR_SERIALNO | VARCHAR2 | ✓ |  | Cdr Serialno |
| CDR_SERIALNO_HASH | VARCHAR2 | ✓ |  | Cdr Serialno Hash |
 | OPERATOR | VARCHAR2 | ✓ |  | Misafir operatörün adı (abonenin roaming sırasında bağlandığı şebeke) | 
 | COUNTRY | VARCHAR2 | ✓ |  | Misafir ülkenin adı — roaming yapılan ülke | 
 | OPERATOR_CODE | VARCHAR2 | ✓ |  | Misafir operatörün kodu (genellikle MCC+MNC veya iç referans kodu) | 
| CALLINGROAMINFO | VARCHAR2 | ✓ |  | Callingroaminfo |
| CALLINGROAMDECIMALINFO | VARCHAR2 | ✓ |  | Callingroamdecimalinfo |
| CALLEDROAMINFO | VARCHAR2 | ✓ |  | Calledroaminfo |
| USAGESERVICETYPE | VARCHAR2 | ✓ |  | Usageservicetype |
| DWH_UPDATE_DATE | DATE | ✓ |  | Dwh Update Date |
| CALLINGROAMCOUNTRYCODE | VARCHAR2 | ✓ |  | Callingroamcountrycode |
| CALLINGROAMAREANUMBER | VARCHAR2 | ✓ |  | Callingroamareanumber |
| CALLINGROAMNETWORKCODE | VARCHAR2 | ✓ |  | Callingroamnetworkcode |
| LAST_ROAM_SIGNAL_COUNTRY | VARCHAR2 | ✓ |  | Last Roam Signal Country |
| LAST_ROAM_SIGNAL_DT | DATE | ✓ |  | Date/timestamp field |

## Keywords

account, acquisition, activation, bandwidth, batch, billing, bundle, call, channel, contract, country, customer, data, date, demographic, etl, financial, geography, income, international, internet, lifecycle, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, roaming, service, snapshot, state, status, subscriber, subscription, tariff, temporal, time, touchpoint, travel, usage, voice
## Business Metadata


### Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **TRANSDATE**: İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi
- **CDR_CATEGORY**: CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS, VAS, roaming vb.)
- **OFFER_ID**: İşlemin altında uygulandığı teklif/kampanya ID'si
- **BILLAMOUNT**: Faturalanan net tutar
- **CHARGEDURATION**: Kullanılan süre, adet veyahut MB
- **OPERATOR**: Misafir operatörün adı (abonenin roaming sırasında bağlandığı şebeke)
- **COUNTRY**: Misafir ülkenin adı — roaming yapılan ülke
- **OPERATOR_CODE**: Misafir operatörün kodu (genellikle MCC+MNC veya iç referans kodu)
