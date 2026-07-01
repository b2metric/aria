---
table: FCT_PREP_REV
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, batch, billing, bundle, call, channel, contract, country, customer, date, demographic, etl, financial, geography, income, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, service, snapshot, subscriber, subscription, tariff, temporal, time, touchpoint, usage, voice]
description: "Fact table containing transactional/event data for Prep Rev"
row_count: 267815014
generated_at: 2026-07-01T22:24:18.306167+00:00
---

# FCT_PREP_REV

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| SUBSCRIBERID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| ACCOUNTID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). |
| NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| PLAN_ID | VARCHAR2 | ✓ |  | Ana tarife/plan ID'si |
| PLAN_NAME | VARCHAR2 | ✓ |  | Ana tarife adı |
| BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. |
| CDR_TYPE | VARCHAR2 | ✓ |  | CDR (Call Detail Record) tipi — kaydın hangi servis tipinden geldiğini gösterir (ses, SMS, data, MMS, VAS, roaming vb.) |
| CHARGINGTYPE | NUMBER | ✓ |  | Chargingtype |
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
| VIRTUAL_IP | NUMBER | ✓ |  | Sanal IP adresi — özellikle data oturumları için abonenin oturum bazlı atanan IP adresi (GGSN/PGW kayıtlarında kullanılır) |
| CDR_SERIALNO_HASH | NUMBER | ✓ |  | CDR_SERIALNO değerinin hash'lenmiş hali — partition/index/maskeleme amaçlı |
| CONTENT_TYPE | VARCHAR2 | ✓ |  | İçerik tipi (müzik, video, oyun, ringback tone, premium SMS, e-kitap vb.) |
| CONTENT_PROVIDER | VARCHAR2 | ✓ |  | İçerik sağlayıcısı — içeriği üreten/sağlayan firma |
| CONTENT_INDIRECT_PROVIDER | VARCHAR2 | ✓ |  | Dolaylı/aracı içerik sağlayıcısı — varsa içeriği ileten ara firma (aggregator hiyerarşisinde alt katman) |
| CONTENT_NAME | VARCHAR2 | ✓ |  | İçeriğin adı (örn. şarkı adı, oyun adı, abonelik servisi adı) |
| CONTENT_CATEGORY | VARCHAR2 | ✓ |  | İçerik kategorisi (üst seviye sınıflandırma — ör. eğlence, eğitim, haber) |
| CONTENT_SUB_CATEGORY | VARCHAR2 | ✓ |  | İçerik alt kategorisi (örn. eğlence > müzik > pop) |
| CONTENT_VIVA_RS_PERCNT | NUMBER | ✓ |  | Operatörün (görünüşe göre marka adı "VIVA") bu içerikten aldığı gelir payı yüzdesi (Revenue Share %) |
| CONTENT_ARGREEGATOR_RS_PERCENT | NUMBER | ✓ |  | Aggregator’ın (içerik aracı firmasının) gelir payı yüzdesi. |
| CONTENT_RENTAL | VARCHAR2 | ✓ |  | İçeriğin abonelik ücreti — kullanıcının bu içerik için ödediği periyodik tutar |
| CONTENT_REV_PERCENT | NUMBER | ✓ |  | İçerikten elde edilen toplam gelirin yüzde dağılımı — net pay sonrası operatör/sağlayıcı bölüşüm oranı |
| CONTENT_COST | NUMBER | ✓ |  | İçeriğin operatöre maliyeti — sağlayıcıya ödenen tutar |
| IS_ROAM_REV | CHAR | ✓ |  | Bu gelir kaydının yurt dışı dolaşımdan (roaming) elde edilip edilmediğini gösteren bayrak (1 = roaming geliri, 0 = yurt içi gelir) |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.306337+00:00*

- **BS_TYPE**: `DATA`, `FIBER`, `FWA`, `VOICE`
- **B_BS_TYPE**: `DATA`, `FIBER`, `FWA`, `M2M`, `VOICE`
- **B_PREPOST_PAID**: `POST`, `PREP`
- **CALLTYPE**: `001`, `002`, `031`, `050`, `051`, `055`, `065`, `070`, `071`, `081`
- **CDR_TYPE**: `BALANCE_RECEIVE`, `BALANCE_TRANSFER`, `CONTENT`, `FORFEITED`, `GPRS`, `INTL_CALL`, `INTL_MMS`, `INTL_SMS`, `IVR`, `LOCAL_CALL`, `LOCAL_MMS`, `LOCAL_SMS`, `OTHER`, `ROAMING`, `SUBSCRIPTION`
- **PREPOST_PAID**: `POST`, `PREP`

<!-- ARIA:ENUM-VALUES-END -->
