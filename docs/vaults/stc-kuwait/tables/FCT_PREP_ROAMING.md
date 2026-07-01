---
table: FCT_PREP_ROAMING
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, bandwidth, batch, billing, bundle, call, channel, contract, country, customer, data, date, demographic, etl, financial, geography, income, international, internet, lifecycle, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, roaming, service, snapshot, state, status, subscriber, subscription, tariff, temporal, time, touchpoint, travel, usage, voice]
description: "Fact table containing transactional/event data for Prep Roaming"
row_count: 41133228
generated_at: 2026-07-01T22:24:18.306923+00:00
---

# FCT_PREP_ROAMING

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). |
| NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. |
| TRANSDATE | DATE | ✗ |  | İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi |
| IMEI | VARCHAR2 | ✓ |  | Imei |
| CALLTYPE | VARCHAR2 | ✓ |  | Calltype |
| CDR_CATEGORY | VARCHAR2 | ✓ |  | CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS, VAS, roaming vb.) |
| CHARGETYPE | VARCHAR2 | ✓ |  | Chargetype |
| INTL_FLAG | CHAR | ✓ |  | Intl Flag |
| USED_NETWORK | CHAR | ✓ |  | Used Network |
| OFFER_ID | VARCHAR2 | ✓ |  | İşlemin altında uygulandığı teklif/kampanya ID'si |
| RENTAL_TYPE | CHAR | ✓ |  | Rental Type |
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
| CHARGEDURATION | NUMBER | ✓ |  | Kullanılan süre, adet veyahut MB |
| CALLDURATION | NUMBER | ✓ |  | Callduration |
| CDR_SERIALNO | VARCHAR2 | ✓ |  | Cdr Serialno |
| CDR_SERIALNO_HASH | NUMBER | ✓ |  | Cdr Serialno Hash |
| OPERATOR | VARCHAR2 | ✓ |  | Misafir operatörün adı (abonenin roaming sırasında bağlandığı şebeke) |
| COUNTRY | VARCHAR2 | ✓ |  | Misafir ülkenin adı — roaming yapılan ülke |
| OPERATOR_CODE | VARCHAR2 | ✓ |  | Misafir operatörün kodu (genellikle MCC+MNC veya iç referans kodu) |
| CALLINGROAMINFO | VARCHAR2 | ✓ |  | Callingroaminfo |
| CALLINGROAMDECIMALINFO | NUMBER | ✓ |  | Callingroamdecimalinfo |
| CALLEDROAMINFO | VARCHAR2 | ✓ |  | Calledroaminfo |
| USAGESERVICETYPE | VARCHAR2 | ✓ |  | Usageservicetype |
| DWH_UPDATE_DATE | DATE | ✓ |  | Dwh Update Date |
| CALLINGROAMCOUNTRYCODE | VARCHAR2 | ✓ |  | Callingroamcountrycode |
| CALLINGROAMAREANUMBER | VARCHAR2 | ✓ |  | Callingroamareanumber |
| CALLINGROAMNETWORKCODE | VARCHAR2 | ✓ |  | Callingroamnetworkcode |
| LAST_ROAM_SIGNAL_COUNTRY | VARCHAR2 | ✓ |  | Last Roam Signal Country |
| LAST_ROAM_SIGNAL_DT | DATE | ✓ |  | Date/timestamp field |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.307222+00:00*

- **BS_TYPE**: `DATA`, `VOICE`
- **CALLINGHOMECODE**: `-1`, `1`, `2`, `3`, `4`, `6`, `871`, `8711`, `8716`, `872`, `873`, `874`, `8819`, `966123`, `973123`
- **CALLINGROAMAREANUMBER**: `-1`, `0`, `1`, `1003`, `1006`, `1007`, `60`
- **CALLINGROAMNETWORKCODE**: `-1`, `0`, `1`, `1001`, `1002`, `1003`, `1200`, `2`, `3`, `3901`, `4`, `6`, `871`, `8711`, `8716`, `873`, `874`, `8819`, `96201`, `966123`, `96650`, `96802`, `97101`, `97102`, `973123`, `973338`, `97401`, `97402`, `9999`
- **CALLTYPE**: `GPRS`, `MOBILE ORIGINATING SMS`, `MOC - Mobile Originating Call`, `MTC - Mobile Terminating Call`
- **CDR_CATEGORY**: `GPRS`, `IVR`, `SMS`, `VOICE`
- **CHARGETYPE**: `ROAM CALL`, `ROAM GPRS`, `ROAM SMS`
- **INTL_FLAG**: `N`
- **PREPOST_PAID**: `POST`, `PREP`
- **RENTAL_TYPE**: `PAYG`
- **USAGESERVICETYPE**: `1120`, `1121`, `1122`, `1123`, `1124`, `1141`, `1142`, `1143`, `1145`, `1321`, `1410`
- **USED_NETWORK**: `OFN`, `ONN`

<!-- ARIA:ENUM-VALUES-END -->
