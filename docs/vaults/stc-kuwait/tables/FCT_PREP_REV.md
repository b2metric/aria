---
table: FCT_PREP_REV
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, batch, billing, bundle, call, channel,
  contract, country, customer, date, demographic, etl, financial, geography, income,
  minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number,
  prepaid, product, provision, revenue, service, snapshot, subscriber, subscription,
  tariff, temporal, time, touchpoint, usage, voice]
generated_at: 2026-06-07 11:22:23.802862+00:00
enriched_at: '2026-06-07T11:22:24.334976+00:00'
---

# FCT_PREP_REV

**Description:** Fact table containing transactional/event data for Prep Rev

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
 | SUBSCRIBERID | NUMBER | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | ACCOUNTID | NUMBER | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | PLAN_ID | NUMBER | ✓ |  | Ana tarife/plan ID'si | 
 | PLAN_NAME | VARCHAR2 | ✓ |  | Ana tarife adı | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. | 
 | CDR_TYPE | VARCHAR2 | ✓ |  | CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS | 
| CHARGINGTYPE | VARCHAR2 | ✓ |  | Chargingtype |
 | BILLAMOUNT | NUMBER | ✓ |  | Faturalanan/tahsil edilen tutar — bu CDR kaydından elde edilen gelir | 
 | LOGDATE | DATE | ✓ |  | Kaydın oluşturulduğu/sisteme düştüğü tarih-zaman damgası | 
| CALLTYPE | VARCHAR2 | ✓ |  | Calltype |
 | CALLINGCELLID | VARCHAR2 | ✓ |  | Arayan tarafın bağlı olduğu baz istasyonu (cell) ID'si — konum tabanlı analitik için kullanılır | 
 | CALLEDCELLID | VARCHAR2 | ✓ |  | Aranan tarafın bağlı olduğu baz istasyonu ID'si | 
 | SERVICEID | VARCHAR2 | ✓ |  | Servis ID'si — işlemin hangi servis/ürün altında ücretlendirildiğini gösterir | 
 | B_SUBNO | VARCHAR2 | ✓ |  | Karşı tarafın abone numarası (MSISDN veya iç ID) | 
 | B_CONTNRO | VARCHAR2 | ✓ |  | Karşı tarafın kontrat numarası (Contract Number — "CONTRNO" olmalı) | 
 | B_CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Karşı tarafın kontrat kategorisi (bireysel, kurumsal, M2M vb.) | 
 | B_NATIONALITY | VARCHAR2 | ✓ |  | Karşı tarafın uyruğu | 
 | B_PREPOST_PAID | VARCHAR2 | ✓ |  | Karşı tarafın hat tipi (ön ödemeli / faturalı) | 
 | B_PLAN_ID | VARCHAR2 | ✓ |  | Karşı tarafın ana tarife/plan ID'si | 
 | B_PLAN_NAME | VARCHAR2 | ✓ |  | Karşı tarafın ana tarife adı | 
 | B_BS_TYPE | VARCHAR2 | ✓ |  | Karşı tarafın temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. | 
 | CDR_SERIALNO | VARCHAR2 | ✓ |  | CDR seri numarası — her bir CDR kaydının benzersiz takip numarası | 
 | VIRTUAL_IP | VARCHAR2 | ✓ |  | Sanal IP adresi — özellikle data oturumları için abonenin oturum bazlı atanan IP adresi (GGSN/PGW ka | 
 | CDR_SERIALNO_HASH | VARCHAR2 | ✓ |  | CDR_SERIALNO değerinin hash'lenmiş hali — partition/index/maskeleme amaçlı | 
 | CONTENT_TYPE | VARCHAR2 | ✓ |  | İçerik tipi (müzik, video, oyun, ringback tone, premium SMS, e-kitap vb.) | 
 | CONTENT_PROVIDER | VARCHAR2 | ✓ |  | İçerik sağlayıcısı — içeriği üreten/sağlayan firma | 
 | CONTENT_INDIRECT_PROVIDER | VARCHAR2 | ✓ |  | Dolaylı/aracı içerik sağlayıcısı — varsa içeriği ileten ara firma (aggregator hiyerarşisinde alt kat | 
 | CONTENT_NAME | VARCHAR2 | ✓ |  | İçeriğin adı (örn. şarkı adı, oyun adı, abonelik servisi adı) | 
 | CONTENT_CATEGORY | VARCHAR2 | ✓ |  | İçerik kategorisi (üst seviye sınıflandırma — ör. eğlence, eğitim, haber) | 
 | CONTENT_SUB_CATEGORY | VARCHAR2 | ✓ |  | İçerik alt kategorisi (örn. eğlence > müzik > pop) | 
 | CONTENT_VIVA_RS_PERCNT | VARCHAR2 | ✓ |  | Operatörün (görünüşe göre marka adı "VIVA") bu içerikten aldığı gelir payı yüzdesi (Revenue Share %) | 
 | CONTENT_ARGREEGATOR_RS_PERCENT | NUMBER | ✓ |  | Aggregator’ın (içerik aracı firmasının) gelir payı yüzdesi. | 
 | CONTENT_RENTAL | NUMBER | ✓ |  | İçeriğin abonelik ücreti — kullanıcının bu içerik için ödediği periyodik tutar | 
 | CONTENT_REV_PERCENT | NUMBER | ✓ |  | İçerikten elde edilen toplam gelirin yüzde dağılımı — net pay sonrası operatör/sağlayıcı bölüşüm ora | 
 | CONTENT_COST | NUMBER | ✓ |  | İçeriğin operatöre maliyeti — sağlayıcıya ödenen tutar | 
 | IS_ROAM_REV | VARCHAR2 | ✓ |  | Bu gelir kaydının yurt dışı dolaşımdan (roaming) elde edilip edilmediğini gösteren bayrak (1 = roami | 

## Keywords

account, acquisition, activation, batch, billing, bundle, call, channel, contract, country, customer, date, demographic, etl, financial, geography, income, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, service, snapshot, subscriber, subscription, tariff, temporal, time, touchpoint, usage, voice
## Business Metadata


### Column Descriptions

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
