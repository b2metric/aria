---
table: DIM_PREP_STATE_SCD2
database: oracle
workspace: stc-kuwait
keywords: [acquisition, batch, channel, date, etl, history, lifecycle, mobile, msisdn,
  phone number, prepaid, slowly changing dimension, snapshot, state, status, subscriber,
  temporal, time, touchpoint, versioned]
generated_at: 2026-06-07 11:22:23.796804+00:00
enriched_at: '2026-06-07T11:22:24.327119+00:00'
---

# DIM_PREP_STATE_SCD2

**Description:** Dimension table containing reference/master data for Prep State Scd2

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Bulk load'ın gerçekleştiği sistem zamanı. | 
 | SNAPSHOT_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir, upsert için yardımcıl fonksiyon, MERGE INTO statement'ında ON koşul | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN bilgisi. | 
 | APPDATE | DATE | ✓ |  | MSISDN'in bir kullanıcı için aktfileştirildiği tarih. Bir numara, farklı zamanlarda farklı kişilerce | 
 | NEXT_APPDATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | PREP olarak tablo boyunca sabit bilgi. | 
 | EFFECTIVE_START_DATE | DATE | ✓ |  | SCD2 tablosu olarak tasarlandığı için, bir gün için bir satırın sadece bir kişi ile eşleşmesi, eğer  | 
 | EFFECTIVE_END_DATE | DATE | ✓ |  | EFFECTIVE_START_DATE ile EFFECTIVE_END_DATE arasında kullanıcının PREPAID_BALANCE ve CURRENT_STATE'e | 
 | CURRENT_STATE | VARCHAR2 | ✓ |  | ACTIVE,DISABLE,GRACE olarak değerler alıp, kullanıcının PREPAID lifecycle döngüsünde hangi aşamada o | 
 | PREPAID_BALANCE | NUMBER | ✓ |  | Kullanıcın, hesabında bulunan bakiye. | 
 | DIM_HASH | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | REVOKE_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | REVOKE_PI_ID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | PREPAID_EFFECTIVE_END_DATE | DATE | ✓ |  | Kullanıcı eğer PREPAID'den POSTPAID'e geçtiyse geçiş tarihini belirtir ve kullanıcının EFFECTIVE_STA | 
 | LIFECYCLE_EFFECTIVE_END_DATE | DATE | ✓ |  | Kullanıcı eğer CHURN olduysa, CHURN tarihini belirittir, ve kullanıcının EFFECTIVE_START_DATE, EFFEC | 

## Keywords

acquisition, batch, channel, date, etl, history, lifecycle, mobile, msisdn, phone number, prepaid, slowly changing dimension, snapshot, state, status, subscriber, temporal, time, touchpoint, versioned
## Business Metadata


### Column Descriptions

- **EXEC_DATE**: Bulk load'ın gerçekleştiği sistem zamanı.
- **SNAPSHOT_DATE**: Önemsiz, kullanılmaması gerekir, upsert için yardımcıl fonksiyon, MERGE INTO statement'ında ON koşulunda kullanılan sütunun, UPDATE SET alanında kullanılamamsından dolayı tekrarlılık var.
- **SUBNO**: MSISDN bilgisi.
- **APPDATE**: MSISDN'in bir kullanıcı için aktfileştirildiği tarih. Bir numara, farklı zamanlarda farklı kişilerce etkinleştirilebileceği, ya da aynı kullanıcının eski numarasını geri talep edebileceği durumu için eklendi.
- **NEXT_APPDATE**: Önemsiz, kullanılmaması gerekir.
- **PREPOST_PAID**: PREP olarak tablo boyunca sabit bilgi.
- **EFFECTIVE_START_DATE**: SCD2 tablosu olarak tasarlandığı için, bir gün için bir satırın sadece bir kişi ile eşleşmesi, eğer BALANCE yada prepaid CURRENT_STATE'i değişirse, değişecek sütun. İlgili kişi, EFFECTIVE_START_DATE, EFFECTIVE_END_DATE zamanları arasında CURRENT_STATE'e (ACTIVE, DISABLE, GRACE) ve PREPAID_BALANCE'ındaki miktara sahiptir anlamı taşıyan tablo bilgisine erişmek için kullanılır.
- **EFFECTIVE_END_DATE**: EFFECTIVE_START_DATE ile EFFECTIVE_END_DATE arasında kullanıcının PREPAID_BALANCE ve CURRENT_STATE'e sahip olduğunu, bu tarihte kullanıcının bu iki bilgisinden birinin değiştiği için farklı bir STATE yada BALANCE'a geçtiğini belirtir. Yeni bilgi, yeni EFFECTIVE_START_DATE olarak farklı bir satırda mevcut olur.
- **CURRENT_STATE**: ACTIVE,DISABLE,GRACE olarak değerler alıp, kullanıcının PREPAID lifecycle döngüsünde hangi aşamada olduğunu belirtir.
- **PREPAID_BALANCE**: Kullanıcın, hesabında bulunan bakiye.
- **DIM_HASH**: Önemsiz, kullanılmaması gerekir.
- **REVOKE_DATE**: Önemsiz, kullanılmaması gerekir.
- **REVOKE_PI_ID**: Önemsiz, kullanılmaması gerekir.
- **PREPAID_EFFECTIVE_END_DATE**: Kullanıcı eğer PREPAID'den POSTPAID'e geçtiyse geçiş tarihini belirtir ve kullanıcının EFFECTIVE_START_DATE, EFFECTIVE_END_DATE tarihleri arasındaki bilgisinin bu tarihten sonra geçersiz olduğunu gösterir.
- **LIFECYCLE_EFFECTIVE_END_DATE**: Kullanıcı eğer CHURN olduysa, CHURN tarihini belirittir, ve kullanıcının EFFECTIVE_START_DATE, EFFECTIVE_END_DATE tarihleri arasındaki bilgisinin bu tarihten sonra geçersiz olduğunu gösterir.
