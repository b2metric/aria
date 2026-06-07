---
table: FCT_PREP_USAGE
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, batch, bundle, channel, contract, country, customer,
  date, demographic, etl, geography, mobile, msisdn, nationality, offer, package,
  phone number, prepaid, product, snapshot, subscriber, tariff, temporal, time, touchpoint]
generated_at: 2026-06-07 11:22:23.803980+00:00
enriched_at: '2026-06-07T11:27:09.137776+00:00'
description: Prepaid subscriber usage metrics fact table
---

# FCT_PREP_USAGE

**Description:** Fact table containing transactional/event data for Prep Usage

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
 | NEXT_APPDATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | PLAN_ID | NUMBER | ✓ |  | Ana tarife/plan ID'si | 
 | TRANSDATE | DATE | ✓ |  | İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi | 
 | CATEGORY | VARCHAR2 | ✓ |  | Kullanım kategorisi (ses, SMS, data, MMS, VAS, roaming vb. üst seviye sınıflandırma) | 
 | NETWORK_DIRECTION | VARCHAR2 | ✓ |  | Şebeke yönü — şebeke içi (on-net) / şebeke dışı (off-net) / uluslararası (international) gibi sınıfl | 
 | OPERATOR_NAME | VARCHAR2 | ✓ |  | İlgili operatörün adı — karşı taraf operatörü ya da roaming durumunda misafir şebeke operatörü | 
| NETWORK_TYPE | VARCHAR2 | ✓ |  | Network Type |
 | BILL_TYPE | VARCHAR2 | ✓ |  | Faturalama tipi — ücretsiz, ücretli | 
 | KPI_TYPE | VARCHAR2 | ✓ |  | KPI'nın tipi/grubu (ör. usage_count, usage_duration, usage_volume, revenue vb.) | 
 | KPI_NAME | VARCHAR2 | ✓ |  | KPI'nın adı (ör. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN v | 
 | KPI_VALUE | NUMBER | ✓ |  | Usage metric value - UPDATED VIA API TEST | 

## Keywords

account, acquisition, batch, bundle, channel, contract, country, customer, date, demographic, etl, geography, mobile, msisdn, nationality, offer, package, phone number, prepaid, product, snapshot, subscriber, tariff, temporal, time, touchpoint
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **NEXT_APPDATE**: Önemsiz, kullanılmaması gerekir.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **PLAN_ID**: Ana tarife/plan ID'si
- **TRANSDATE**: İşlem/kullanım tarihi (Transaction Date) — KPI değerinin ait olduğu gerçek kullanım tarihi
- **CATEGORY**: Kullanım kategorisi (ses, SMS, data, MMS, VAS, roaming vb. üst seviye sınıflandırma)
- **NETWORK_DIRECTION**: Şebeke yönü — şebeke içi (on-net) / şebeke dışı (off-net) / uluslararası (international) gibi sınıflandırma
- **OPERATOR_NAME**: İlgili operatörün adı — karşı taraf operatörü ya da roaming durumunda misafir şebeke operatörü
- **BILL_TYPE**: Faturalama tipi — ücretsiz, ücretli
- **KPI_TYPE**: KPI'nın tipi/grubu (ör. usage_count, usage_duration, usage_volume, revenue vb.)
- **KPI_NAME**: KPI'nın adı (ör. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN vb.)
- **KPI_VALUE**: KPI'nın değeri — ilgili metriğin sayısal karşılığı (dakika, adet, MB, TL vb.)
## Business Metadata

**Description:** Prepaid subscriber usage metrics fact table

### Column Descriptions

- **KPI_VALUE**: Usage metric value - UPDATED VIA API TEST
