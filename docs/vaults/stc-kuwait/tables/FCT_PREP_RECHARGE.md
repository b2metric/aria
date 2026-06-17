---
table: FCT_PREP_RECHARGE
database: oracle
workspace: stc-kuwait
keywords: [TL loading, TL yükleme, balance, ball up, loading, payment, prepaid, recharge,
  top up, top-up, yükleme]
generated_at: '2026-06-16T03:23:43.169499+00:00'
enriched_at: '2026-06-16T14:59:52.300825+00:00'
description: Fact table showing the details and amounts of top-up, recharge transactions
  of prepaid subscribers.
---

# FCT_PREP_RECHARGE

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
 | SUBSCRIBERID | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
 | RECHARGE_DATE | DATE | ✓ |  | Date/time stamp when KD upload occurred | 
 | PREPAIDBALANCEBEFORE | NUMBER | ✓ |  | Main balance in the account before recharge. | 
 | TOPUP_SEQ | NUMBER | ✓ |  | Sequence number of the upload process — the unique identifier (primary key) of the process | 
| SERIAL_NUMBER | VARCHAR2 | ✓ |  |  |
 | ITEM_CODE | VARCHAR2 | ✓ |  | Installation product code — e.g. code of a specific voucher type or download package | 
 | ITEM_NO | VARCHAR2 | ✓ |  | ITEM serial number — tracking number used for stock system reference purposes | 
 | VOUCHER_TYPE | VARCHAR2 | ✓ |  | Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.) | 
 | TOPUP_AMOUNT | NUMBER | ✓ |  | Loaded amount (KD) | 
| OPERATEDBY | VARCHAR2 | ✓ |  |  |
| THIRDPARTYNUMBER | VARCHAR2 | ✓ |  |  |
| TRADETYPE | VARCHAR2 | ✓ |  |  |
| ACCESSMETHOD | VARCHAR2 | ✓ |  |  |
| CHANNEL | VARCHAR2 | ✓ |  |  |
| CHANNELNAME | VARCHAR2 | ✓ |  |  |
 | TOPUP_SEQ_HASH | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **CONTRNO**: 
- **SUBNO**: 
- **APPDATE**: 
- **SUBSCRIBERID**: 
- **CONTRACT_CATEGORY**: 
- **NATIONALITY**: 
- **PREPOST_PAID**: 
- **BS_TYPE**: 
- **RECHARGE_DATE**: 
- **PREPAIDBALANCEBEFORE**: 
- **TOPUP_SEQ**: 
- **SERIAL_NUMBER**: 
- **ITEM_CODE**: 
- **ITEM_NO**: 
- **VOUCHER_TYPE**: 
- **TOPUP_AMOUNT**: 
- **OPERATEDBY**: 
- **THIRDPARTYNUMBER**: 
- **TRADETYPE**: 
- **ACCESSMETHOD**: 
- **CHANNEL**: 
- **CHANNELNAME**: 
- **TOPUP_SEQ_HASH**:
## Column Descriptions

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
## Column Descriptions

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
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
## Business Metadata

**Description:** Fact table showing the details and amounts of top-up, recharge transactions of prepaid subscribers.

### Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **APPDATE**: Line's activation / contract start date (Application Date).
- **SUBSCRIBERID**: It is unimportant and should not be used.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **PREPOST_PAID**: It is unimportant and should not be used.
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **RECHARGE_DATE**: Date/time stamp when KD upload occurred
- **PREPAIDBALANCEBEFORE**: Main balance in the account before recharge.
- **TOPUP_SEQ**: Sequence number of the upload process — the unique identifier (primary key) of the process
- **ITEM_CODE**: Installation product code — e.g. code of a specific voucher type or download package
- **ITEM_NO**: ITEM serial number — tracking number used for stock system reference purposes
- **VOUCHER_TYPE**: Top-up voucher type (physical scratch-card, electronic voucher, online top-up, credit card, e-pin, etc.)
- **TOPUP_AMOUNT**: Loaded amount (KD)
- **TOPUP_SEQ_HASH**: It is unimportant and should not be used.
