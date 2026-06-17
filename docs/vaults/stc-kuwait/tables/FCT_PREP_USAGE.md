---
table: FCT_PREP_USAGE
database: oracle
workspace: stc-kuwait
keywords: [data, kullanım, prepaid, sms, traffic, trafik, usage, use, voice]
generated_at: '2026-06-16T03:23:43.170686+00:00'
enriched_at: '2026-06-16T14:59:52.305624+00:00'
description: Fact table that keeps basic data, voice and SMS usage details of prepaid
  subscribers on the domestic network.
---

# FCT_PREP_USAGE

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | NEXT_APPDATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | PLAN_ID | NUMBER | ✓ |  | Main tariff/plan ID | 
 | TRANSDATE | DATE | ✓ |  | Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs | 
 | CATEGORY | VARCHAR2 | ✓ |  | Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.) | 
 | NETWORK_DIRECTION | VARCHAR2 | ✓ |  | Network direction — classification such as on-net / off-net / international | 
 | OPERATOR_NAME | VARCHAR2 | ✓ |  | Name of the relevant operator — counterparty operator or guest network operator in case of roaming | 
| NETWORK_TYPE | VARCHAR2 | ✓ |  |  |
 | BILL_TYPE | VARCHAR2 | ✓ |  | Billing type — free, paid | 
 | KPI_TYPE | VARCHAR2 | ✓ |  | Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.) | 
 | KPI_NAME | VARCHAR2 | ✓ |  | Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.) | 
 | KPI_VALUE | NUMBER | ✓ |  | The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.) | 

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **CONTRNO**: 
- **SUBNO**: 
- **APPDATE**: 
- **NEXT_APPDATE**: 
- **CONTRACT_CATEGORY**: 
- **NATIONALITY**: 
- **PREPOST_PAID**: 
- **PLAN_ID**: 
- **TRANSDATE**: 
- **CATEGORY**: 
- **NETWORK_DIRECTION**: 
- **OPERATOR_NAME**: 
- **NETWORK_TYPE**: 
- **BILL_TYPE**: 
- **KPI_TYPE**: 
- **KPI_NAME**: 
- **KPI_VALUE**:
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
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
## Business Metadata

**Description:** Fact table that keeps basic data, voice and SMS usage details of prepaid subscribers on the domestic network.

### Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **TRANSDATE**: Transaction/usage date (Transaction Date) — The actual usage date to which the KPI value belongs
- **CATEGORY**: Usage category (upper level classification such as voice, SMS, data, MMS, VAS, roaming, etc.)
- **NETWORK_DIRECTION**: Network direction — classification such as on-net / off-net / international
- **OPERATOR_NAME**: Name of the relevant operator — counterparty operator or guest network operator in case of roaming
- **BILL_TYPE**: Billing type — free, paid
- **KPI_TYPE**: Type/group of KPI (e.g. usage_count, usage_duration, usage_volume, revenue, etc.)
- **KPI_NAME**: Name of the KPI (e.g. VOICE_ONNET_MIN, SMS_OFFNET_CNT, DATA_LOCAL_MB, ROAMING_VOICE_MIN, VOICE_INTL_MIN, etc.)
- **KPI_VALUE**: The value of the KPI — the numerical equivalent of the relevant metric (minutes, units, MB, TL, etc.)
