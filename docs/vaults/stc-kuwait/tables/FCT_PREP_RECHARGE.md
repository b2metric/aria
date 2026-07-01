---
table: FCT_PREP_RECHARGE
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, balance, bandwidth, batch, billing, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, income, internet, mobile, money, msisdn, nationality, payment, phone number, prepaid, recharge, revenue, snapshot, subscriber, temporal, time, topup, touchpoint, usage]
description: "Fact table containing transactional/event data for Prep Recharge"
row_count: 18419866
generated_at: 2026-07-01T22:24:18.305513+00:00
---

# FCT_PREP_RECHARGE

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| SUBSCRIBERID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
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
| VOUCHER_TYPE | VARCHAR2 | ✓ |  | Yükleme kuponu tipi (fiziksel scratch-card, elektronik voucher, online yükleme, kredi kartı, e-pin vb.) |
| TOPUP_AMOUNT | NUMBER | ✓ |  | Yüklenen tutar (KD) |
| OPERATEDBY | VARCHAR2 | ✓ |  | Operatedby |
| THIRDPARTYNUMBER | VARCHAR2 | ✓ |  | Thirdpartynumber |
| TRADETYPE | VARCHAR2 | ✓ |  | Tradetype |
| ACCESSMETHOD | VARCHAR2 | ✓ |  | Accessmethod |
| CHANNEL | VARCHAR2 | ✓ |  | Transaction channel |
| CHANNELNAME | VARCHAR2 | ✓ |  | Transaction channel |
| TOPUP_SEQ_HASH | NUMBER | ✓ |  | Önemsiz, kullanılmaması gerekir. |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.305666+00:00*

- **ACCESSMETHOD**: `0`, `1`, `3`, `4`, `5`, `6`
- **BS_TYPE**: `DATA`, `FIBER`, `VOICE`
- **CHANNEL**: `DIGITAL CHANNEL`, `E-DEALERS RECHARGE`
- **CHANNELNAME**: `B2BKIOSK`, `DMS`, `IPHONE`, `KIOSK`, `WEB`
- **ITEM_CODE**: `EV02`, `EV03`, `EV05`, `EV06`, `EV1.5`, `EV10`, `EV20`, `EV25`, `EVI05`, `RC1.5`, `RCQ02`, `RCQ03`, `RCQ05`, `RCQ06`, `RCQ1.5`, `RCQ10`, `RCQ20`, `RCQ25`
- **PREPOST_PAID**: `POST`, `PREP`
- **TRADETYPE**: `0`, `1102`, `1103`, `1108`, `1109`, `1112`, `1113`, `2`, `5`, `6`, `7`, `900`
- **VOUCHER_TYPE**: `E-Voucher`, `Electronic Top-Up`, `OTHER`, `Other Recharge`, `Physical Voucher`

<!-- ARIA:ENUM-VALUES-END -->
