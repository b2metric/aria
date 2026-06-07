---
table: FCT_PREP_RECHARGE
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, balance, bandwidth, batch, billing, channel, contract,
  country, credit, customer, data, date, demographic, etl, financial, geography, income,
  internet, mobile, money, msisdn, nationality, payment, phone number, prepaid, recharge,
  revenue, snapshot, subscriber, temporal, time, topup, touchpoint, usage]
generated_at: 2026-06-07 11:22:23.802249+00:00
enriched_at: '2026-06-07T11:22:24.333741+00:00'
---

# FCT_PREP_RECHARGE

**Description:** Fact table containing transactional/event data for Prep Recharge

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
 | SUBSCRIBERID | NUMBER | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. | 
 | RECHARGE_DATE | DATE | ✓ |  | KD yükleme işleminin gerçekleştiği tarih/zaman damgası | 
 | PREPAIDBALANCEBEFORE | NUMBER | ✓ |  | Recharge öncesi hesapta bulunan ana bakiye. | 
 | TOPUP_SEQ | NUMBER | ✓ |  | Yükleme işleminin sıra/sequence numarası — işlemin benzersiz tanımlayıcısı (primary key niteliğinde) | 
| SERIAL_NUMBER | VARCHAR2 | ✓ |  | Serial Number |
 | ITEM_CODE | VARCHAR2 | ✓ |  | Yükleme ürününü kodu — örn. belirli bir voucher tipi veya yükleme paketinin kodu | 
 | ITEM_NO | VARCHAR2 | ✓ |  | ITEM seri numarası — stok sistemi referans amacıyla kullanılan takip numarası | 
 | VOUCHER_TYPE | VARCHAR2 | ✓ |  | Yükleme kuponu tipi (fiziksel scratch-card, elektronik voucher, online yükleme, kredi kartı, e-pin v | 
 | TOPUP_AMOUNT | NUMBER | ✓ |  | Yüklenen tutar (KD) | 
| OPERATEDBY | VARCHAR2 | ✓ |  | Operatedby |
| THIRDPARTYNUMBER | VARCHAR2 | ✓ |  | Thirdpartynumber |
| TRADETYPE | VARCHAR2 | ✓ |  | Tradetype |
| ACCESSMETHOD | VARCHAR2 | ✓ |  | Accessmethod |
| CHANNEL | VARCHAR2 | ✓ |  | Transaction channel |
| CHANNELNAME | VARCHAR2 | ✓ |  | Transaction channel |
 | TOPUP_SEQ_HASH | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 

## Keywords

account, acquisition, balance, bandwidth, batch, billing, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, income, internet, mobile, money, msisdn, nationality, payment, phone number, prepaid, recharge, revenue, snapshot, subscriber, temporal, time, topup, touchpoint, usage
## Business Metadata


### Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **SUBSCRIBERID**: Önemsiz, kullanılmaması gerekir.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **RECHARGE_DATE**: KD yükleme işleminin gerçekleştiği tarih/zaman damgası
- **PREPAIDBALANCEBEFORE**: Recharge öncesi hesapta bulunan ana bakiye.
- **TOPUP_SEQ**: Yükleme işleminin sıra/sequence numarası — işlemin benzersiz tanımlayıcısı (primary key niteliğinde)
- **ITEM_CODE**: Yükleme ürününü kodu — örn. belirli bir voucher tipi veya yükleme paketinin kodu
- **ITEM_NO**: ITEM seri numarası — stok sistemi referans amacıyla kullanılan takip numarası
- **VOUCHER_TYPE**: Yükleme kuponu tipi (fiziksel scratch-card, elektronik voucher, online yükleme, kredi kartı, e-pin vb.)
- **TOPUP_AMOUNT**: Yüklenen tutar (KD)
- **TOPUP_SEQ_HASH**: Önemsiz, kullanılmaması gerekir.
