---
table: FCT_PREP_USAGE
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, batch, bundle, channel, contract, country, customer, date, demographic, etl, geography, mobile, msisdn, nationality, offer, package, phone number, prepaid, product, snapshot, subscriber, tariff, temporal, time, touchpoint]
description: "Fact table containing transactional/event data for Prep Usage"
row_count: 1709105189
generated_at: 2026-07-01T22:24:18.307554+00:00
---

# FCT_PREP_USAGE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| NEXT_APPDATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). |
| NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| PLAN_ID | VARCHAR2 | ✓ |  | Ana tarife/plan ID'si |
| TRANSDATE | DATE | ✓ |  | İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi |
| CATEGORY | VARCHAR2 | ✓ |  | Kullanım kategorisi (ses, SMS, data, MMS, VAS, roaming vb. üst seviye sınıflandırma) |
| NETWORK_DIRECTION | CHAR | ✓ |  | Şebeke yönü — şebeke içi (on-net) / şebeke dışı (off-net) / uluslararası (international) gibi sınıflandırma |
| OPERATOR_NAME | VARCHAR2 | ✓ |  | İlgili operatörün adı — karşı taraf operatörü ya da roaming durumunda misafir şebeke operatörü |
| NETWORK_TYPE | VARCHAR2 | ✓ |  | Network Type |
| BILL_TYPE | CHAR | ✓ |  | Faturalama tipi — ücretsiz, ücretli |
| KPI_TYPE | VARCHAR2 | ✓ |  | KPI'nın tipi/grubu (ör. usage_count, usage_duration, usage_volume, revenue vb.) |
| KPI_NAME | VARCHAR2 | ✓ |  | KPI'nın adı (ör. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN vb.) |
| KPI_VALUE | NUMBER | ✓ |  | KPI'nın değeri — ilgili metriğin sayısal karşılığı (dakika, adet, MB, TL vb.) |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.307644+00:00*

- **BILL_TYPE**: `FREE`, `PAID`
- **CATEGORY**: `DATA`, `SMS`, `VOICE`
- **KPI_TYPE**: `COUNT`, `MOU`, `REV`, `USAGE_MB`
- **NETWORK_DIRECTION**: `INCOMING`, `OUTGOING`
- **NETWORK_TYPE**: `INTERNATIONAL`, `OF-NET`, `ON-NET`
- **OPERATOR_NAME**: `PSTN`, `WATANIYA`, `ZAIN`
- **PREPOST_PAID**: `POST`, `PREP`

<!-- ARIA:ENUM-VALUES-END -->
