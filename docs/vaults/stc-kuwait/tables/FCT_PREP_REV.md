---
table: FCT_PREP_REV
database: oracle
workspace: stc-kuwait
keywords: [finance, financial, finans, gelir, income, prepaid, revenue]
generated_at: '2026-06-16T03:23:43.169891+00:00'
enriched_at: '2026-06-16T14:59:52.302618+00:00'
description: Fact table showing revenue movements and financial reflections obtained
  from prepaid subscribers.
---

# FCT_PREP_REV

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE. | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | SUBSCRIBERID | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | ACCOUNTID | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | PLAN_ID | NUMBER | ✓ |  | Main tariff/plan ID | 
 | PLAN_NAME | VARCHAR2 | ✓ |  | Main tariff name | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
 | CDR_TYPE | VARCHAR2 | ✓ |  | CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.) | 
| CHARGINGTYPE | VARCHAR2 | ✓ |  |  |
 | BILLAMOUNT | NUMBER | ✓ |  | Amount billed/collected — revenue from this CDR record | 
 | LOGDATE | DATE | ✓ |  | Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing. | 
| CALLTYPE | VARCHAR2 | ✓ |  |  |
 | CALLINGCELLID | VARCHAR2 | ✓ |  | Base station (cell) ID to which the calling party is connected — used for location-based analytics | 
 | CALLEDCELLID | VARCHAR2 | ✓ |  | Base station ID to which the called party is connected | 
 | SERVICEID | VARCHAR2 | ✓ |  | Service ID — indicates under which service/product the transaction is charged | 
 | B_SUBNO | VARCHAR2 | ✓ |  | Subscriber number of the other party (MSISDN or internal ID) | 
 | B_CONTNRO | VARCHAR2 | ✓ |  | Contract number of the other party (Contract Number - must be "CONTRNO") | 
 | B_CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category of the counterparty (individual, corporate, M2M, etc.) | 
 | B_NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the other party | 
 | B_PREPOST_PAID | VARCHAR2 | ✓ |  | Line type of the other party (prepaid / postpaid) | 
 | B_PLAN_ID | VARCHAR2 | ✓ |  | Main tariff/plan ID of the other party | 
 | B_PLAN_NAME | VARCHAR2 | ✓ |  | Main tariff name of the counterparty | 
 | B_BS_TYPE | VARCHAR2 | ✓ |  | Basic service type of the counterparty — e.g. voice, data, M2M. | 
 | CDR_SERIALNO | VARCHAR2 | ✓ |  | CDR serial number — the unique tracking number of each CDR record | 
 | VIRTUAL_IP | VARCHAR2 | ✓ |  | Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records) | 
 | CDR_SERIALNO_HASH | VARCHAR2 | ✓ |  | Hashed version of CDR_SERIALNO — for partition/index/masking purposes | 
 | CONTENT_TYPE | VARCHAR2 | ✓ |  | Content type (music, video, game, ringback tone, premium SMS, e-book, etc.) | 
 | CONTENT_PROVIDER | VARCHAR2 | ✓ |  | Content provider — the company that produces/provides the content | 
 | CONTENT_INDIRECT_PROVIDER | VARCHAR2 | ✓ |  | Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy) | 
 | CONTENT_NAME | VARCHAR2 | ✓ |  | Name of the content (e.g. song title, game name, subscription service name) | 
 | CONTENT_CATEGORY | VARCHAR2 | ✓ |  | Content category (top-level classification — e.g. entertainment, education, news) | 
 | CONTENT_SUB_CATEGORY | VARCHAR2 | ✓ |  | Content subcategory (e.g. entertainment > music > pop) | 
 | CONTENT_VIVA_RS_PERCNT | VARCHAR2 | ✓ |  | The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %) | 
 | CONTENT_ARGREEGATOR_RS_PERCENT | NUMBER | ✓ |  | Aggregator's (content broker's) percentage of revenue share. | 
 | CONTENT_RENTAL | NUMBER | ✓ |  | Subscription fee for content — the periodic amount the user pays for this content | 
 | CONTENT_REV_PERCENT | NUMBER | ✓ |  | Percentage distribution of total revenue from content — operator/provider split ratio after net share | 
 | CONTENT_COST | NUMBER | ✓ |  | The cost of the content to the operator — the amount paid to the provider | 
 | IS_ROAM_REV | VARCHAR2 | ✓ |  | Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue) | 

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **CONTRNO**: 
- **SUBNO**: 
- **APPDATE**: 
- **SUBSCRIBERID**: 
- **ACCOUNTID**: 
- **CONTRACT_CATEGORY**: 
- **NATIONALITY**: 
- **PREPOST_PAID**: 
- **PLAN_ID**: 
- **PLAN_NAME**: 
- **BS_TYPE**: 
- **CDR_TYPE**: 
- **CHARGINGTYPE**: 
- **BILLAMOUNT**: 
- **LOGDATE**: 
- **CALLTYPE**: 
- **CALLINGCELLID**: 
- **CALLEDCELLID**: 
- **SERVICEID**: 
- **B_SUBNO**: 
- **B_CONTNRO**: 
- **B_CONTRACT_CATEGORY**: 
- **B_NATIONALITY**: 
- **B_PREPOST_PAID**: 
- **B_PLAN_ID**: 
- **B_PLAN_NAME**: 
- **B_BS_TYPE**: 
- **CDR_SERIALNO**: 
- **VIRTUAL_IP**: 
- **CDR_SERIALNO_HASH**: 
- **CONTENT_TYPE**: 
- **CONTENT_PROVIDER**: 
- **CONTENT_INDIRECT_PROVIDER**: 
- **CONTENT_NAME**: 
- **CONTENT_CATEGORY**: 
- **CONTENT_SUB_CATEGORY**: 
- **CONTENT_VIVA_RS_PERCNT**: 
- **CONTENT_ARGREEGATOR_RS_PERCENT**: 
- **CONTENT_RENTAL**: 
- **CONTENT_REV_PERCENT**: 
- **CONTENT_COST**: 
- **IS_ROAM_REV**:
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **SUBSCRIBERID**: Önemsiz, kullanılmaması gerekir.
- **ACCOUNTID**: Önemsiz, kullanılmaması gerekir.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **PLAN_ID**: Ana tarife/plan ID'si
- **PLAN_NAME**: Ana tarife adı
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS, VAS, roaming vb.)
- **BILLAMOUNT**: Faturalanan/tahsil edilen tutar — bu CDR kaydından elde edilen gelir
- **LOGDATE**: Kaydın oluşturulduğu/sisteme düştüğü tarih-zaman damgası
- **CALLINGCELLID**: Arayan tarafın bağlı olduğu baz istasyonu (cell) ID'si — konum tabanlı analitik için kullanılır
- **CALLEDCELLID**: Aranan tarafın bağlı olduğu baz istasyonu ID'si
- **SERVICEID**: Servis ID'si — işlemin hangi servis/ürün altında ücretlendirildiğini gösterir
- **B_SUBNO**: Karşı tarafın abone numarası (MSISDN veya iç ID)
- **B_CONTNRO**: Karşı tarafın kontrat numarası (Contract Number — "CONTRNO" olmalı)
- **B_CONTRACT_CATEGORY**: Karşı tarafın kontrat kategorisi (bireysel, kurumsal, M2M vb.)
- **B_NATIONALITY**: Karşı tarafın uyruğu
- **B_PREPOST_PAID**: Karşı tarafın hat tipi (ön ödemeli / faturalı)
- **B_PLAN_ID**: Karşı tarafın ana tarife/plan ID'si
- **B_PLAN_NAME**: Karşı tarafın ana tarife adı
- **B_BS_TYPE**: Karşı tarafın temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **CDR_SERIALNO**: CDR seri numarası — her bir CDR kaydının benzersiz takip numarası
- **VIRTUAL_IP**: Sanal IP adresi — özellikle data oturumları için abonenin oturum bazlı atanan IP adresi (GGSN/PGW kayıtlarında kullanılır)
- **CDR_SERIALNO_HASH**: CDR_SERIALNO değerinin hash'lenmiş hali — partition/index/maskeleme amaçlı
- **CONTENT_TYPE**: İçerik tipi (müzik, video, oyun, ringback tone, premium SMS, e-kitap vb.)
- **CONTENT_PROVIDER**: İçerik sağlayıcısı — içeriği üreten/sağlayan firma
- **CONTENT_INDIRECT_PROVIDER**: Dolaylı/aracı içerik sağlayıcısı — varsa içeriği ileten ara firma (aggregator hiyerarşisinde alt katman)
- **CONTENT_NAME**: İçeriğin adı (örn. şarkı adı, oyun adı, abonelik servisi adı)
- **CONTENT_CATEGORY**: İçerik kategorisi (üst seviye sınıflandırma — ör. eğlence, eğitim, haber)
- **CONTENT_SUB_CATEGORY**: İçerik alt kategorisi (örn. eğlence > müzik > pop)
- **CONTENT_VIVA_RS_PERCNT**: Operatörün (görünüşe göre marka adı "VIVA") bu içerikten aldığı gelir payı yüzdesi (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator’ın (içerik aracı firmasının) gelir payı yüzdesi.
- **CONTENT_RENTAL**: İçeriğin abonelik ücreti — kullanıcının bu içerik için ödediği periyodik tutar
- **CONTENT_REV_PERCENT**: İçerikten elde edilen toplam gelirin yüzde dağılımı — net pay sonrası operatör/sağlayıcı bölüşüm oranı
- **CONTENT_COST**: İçeriğin operatöre maliyeti — sağlayıcıya ödenen tutar
- **IS_ROAM_REV**: Bu gelir kaydının yurt dışı dolaşımdan (roaming) elde edilip edilmediğini gösteren bayrak (1 = roaming geliri, 0 = yurt içi gelir)
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **SUBSCRIBERID**: Önemsiz, kullanılmaması gerekir.
- **ACCOUNTID**: Önemsiz, kullanılmaması gerekir.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **PLAN_ID**: Ana tarife/plan ID'si
- **PLAN_NAME**: Ana tarife adı
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS, VAS, roaming vb.)
- **BILLAMOUNT**: Faturalanan/tahsil edilen tutar — bu CDR kaydından elde edilen gelir
- **LOGDATE**: Kaydın oluşturulduğu/sisteme düştüğü tarih-zaman damgası
- **CALLINGCELLID**: Arayan tarafın bağlı olduğu baz istasyonu (cell) ID'si — konum tabanlı analitik için kullanılır
- **CALLEDCELLID**: Aranan tarafın bağlı olduğu baz istasyonu ID'si
- **SERVICEID**: Servis ID'si — işlemin hangi servis/ürün altında ücretlendirildiğini gösterir
- **B_SUBNO**: Karşı tarafın abone numarası (MSISDN veya iç ID)
- **B_CONTNRO**: Karşı tarafın kontrat numarası (Contract Number — "CONTRNO" olmalı)
- **B_CONTRACT_CATEGORY**: Karşı tarafın kontrat kategorisi (bireysel, kurumsal, M2M vb.)
- **B_NATIONALITY**: Karşı tarafın uyruğu
- **B_PREPOST_PAID**: Karşı tarafın hat tipi (ön ödemeli / faturalı)
- **B_PLAN_ID**: Karşı tarafın ana tarife/plan ID'si
- **B_PLAN_NAME**: Karşı tarafın ana tarife adı
- **B_BS_TYPE**: Karşı tarafın temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **CDR_SERIALNO**: CDR seri numarası — her bir CDR kaydının benzersiz takip numarası
- **VIRTUAL_IP**: Sanal IP adresi — özellikle data oturumları için abonenin oturum bazlı atanan IP adresi (GGSN/PGW kayıtlarında kullanılır)
- **CDR_SERIALNO_HASH**: CDR_SERIALNO değerinin hash'lenmiş hali — partition/index/maskeleme amaçlı
- **CONTENT_TYPE**: İçerik tipi (müzik, video, oyun, ringback tone, premium SMS, e-kitap vb.)
- **CONTENT_PROVIDER**: İçerik sağlayıcısı — içeriği üreten/sağlayan firma
- **CONTENT_INDIRECT_PROVIDER**: Dolaylı/aracı içerik sağlayıcısı — varsa içeriği ileten ara firma (aggregator hiyerarşisinde alt katman)
- **CONTENT_NAME**: İçeriğin adı (örn. şarkı adı, oyun adı, abonelik servisi adı)
- **CONTENT_CATEGORY**: İçerik kategorisi (üst seviye sınıflandırma — ör. eğlence, eğitim, haber)
- **CONTENT_SUB_CATEGORY**: İçerik alt kategorisi (örn. eğlence > müzik > pop)
- **CONTENT_VIVA_RS_PERCNT**: Operatörün (görünüşe göre marka adı "VIVA") bu içerikten aldığı gelir payı yüzdesi (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator’ın (içerik aracı firmasının) gelir payı yüzdesi.
- **CONTENT_RENTAL**: İçeriğin abonelik ücreti — kullanıcının bu içerik için ödediği periyodik tutar
- **CONTENT_REV_PERCENT**: İçerikten elde edilen toplam gelirin yüzde dağılımı — net pay sonrası operatör/sağlayıcı bölüşüm oranı
- **CONTENT_COST**: İçeriğin operatöre maliyeti — sağlayıcıya ödenen tutar
- **IS_ROAM_REV**: Bu gelir kaydının yurt dışı dolaşımdan (roaming) elde edilip edilmediğini gösteren bayrak (1 = roaming geliri, 0 = yurt içi gelir)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
## Business Metadata

**Description:** Fact table showing revenue movements and financial reflections obtained from prepaid subscribers.

### Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date). Also used as the REVENUE DATE.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **ACCOUNTID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **PLAN_ID**: Main tariff/plan ID
- **PLAN_NAME**: Main tariff name
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **CDR_TYPE**: CDR (Call Detail Record) type — indicates which service type the record comes from (voice, SMS, data, MMS, VAS, roaming, etc.)
- **BILLAMOUNT**: Amount billed/collected — revenue from this CDR record
- **LOGDATE**: Date-time stamp when the record was created/entered the system. Use this as the main DATE for revenue and billing.
- **CALLINGCELLID**: Base station (cell) ID to which the calling party is connected — used for location-based analytics
- **CALLEDCELLID**: Base station ID to which the called party is connected
- **SERVICEID**: Service ID — indicates under which service/product the transaction is charged
- **B_SUBNO**: Subscriber number of the other party (MSISDN or internal ID)
- **B_CONTNRO**: Contract number of the other party (Contract Number - must be "CONTRNO")
- **B_CONTRACT_CATEGORY**: Contract category of the counterparty (individual, corporate, M2M, etc.)
- **B_NATIONALITY**: Nationality of the other party
- **B_PREPOST_PAID**: Line type of the other party (prepaid / postpaid)
- **B_PLAN_ID**: Main tariff/plan ID of the other party
- **B_PLAN_NAME**: Main tariff name of the counterparty
- **B_BS_TYPE**: Basic service type of the counterparty — e.g. voice, data, M2M.
- **CDR_SERIALNO**: CDR serial number — the unique tracking number of each CDR record
- **VIRTUAL_IP**: Virtual IP address — session-based assigned IP address of the subscriber, especially for data sessions (used in GGSN/PGW records)
- **CDR_SERIALNO_HASH**: Hashed version of CDR_SERIALNO — for partition/index/masking purposes
- **CONTENT_TYPE**: Content type (music, video, game, ringback tone, premium SMS, e-book, etc.)
- **CONTENT_PROVIDER**: Content provider — the company that produces/provides the content
- **CONTENT_INDIRECT_PROVIDER**: Indirect/intermediary content provider — the intermediate company that delivers the content, if any (lower layer in the aggregator hierarchy)
- **CONTENT_NAME**: Name of the content (e.g. song title, game name, subscription service name)
- **CONTENT_CATEGORY**: Content category (top-level classification — e.g. entertainment, education, news)
- **CONTENT_SUB_CATEGORY**: Content subcategory (e.g. entertainment > music > pop)
- **CONTENT_VIVA_RS_PERCNT**: The operator's (apparently brand name "VIVA") percentage of revenue share from this content (Revenue Share %)
- **CONTENT_ARGREEGATOR_RS_PERCENT**: Aggregator's (content broker's) percentage of revenue share.
- **CONTENT_RENTAL**: Subscription fee for content — the periodic amount the user pays for this content
- **CONTENT_REV_PERCENT**: Percentage distribution of total revenue from content — operator/provider split ratio after net share
- **CONTENT_COST**: The cost of the content to the operator — the amount paid to the provider
- **IS_ROAM_REV**: Flag indicating whether this revenue record is derived from international roaming (1 = roaming revenue, 0 = domestic revenue)
