---
table: DIM_PREP_STATE_SCD2
database: oracle
workspace: stc-kuwait
keywords: [acquisition, batch, channel, date, etl, history, lifecycle, mobile, msisdn, phone number, prepaid, slowly changing dimension, snapshot, state, status, subscriber, temporal, time, touchpoint, versioned]
description: "Dimension table containing reference/master data for Prep State Scd2"
row_count: 20746505
generated_at: 2026-07-01T22:24:18.299954+00:00
---

# DIM_PREP_STATE_SCD2

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Bulk load'ın gerçekleştiği sistem zamanı. |
| SNAPSHOT_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir, upsert için yardımcıl fonksiyon, MERGE INTO statement'ında ON koşulunda kullanılan sütunun, UPDATE SET alanında kullanılamamsından dolayı tekrarlılık var. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN bilgisi. |
| APPDATE | DATE | ✓ |  | MSISDN'in bir kullanıcı için aktfileştirildiği tarih. Bir numara, farklı zamanlarda farklı kişilerce etkinleştirilebileceği, ya da aynı kullanıcının eski numarasını geri talep edebileceği durumu için eklendi. |
| NEXT_APPDATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| PREPOST_PAID | CHAR | ✓ |  | PREP olarak tablo boyunca sabit bilgi. |
| EFFECTIVE_START_DATE | DATE | ✓ |  | SCD2 tablosu olarak tasarlandığı için, bir gün için bir satırın sadece bir kişi ile eşleşmesi, eğer BALANCE yada prepaid CURRENT_STATE'i değişirse, değişecek sütun. İlgili kişi, EFFECTIVE_START_DATE, EFFECTIVE_END_DATE zamanları arasında CURRENT_STATE'e (ACTIVE, DISABLE, GRACE) ve PREPAID_BALANCE'ındaki miktara sahiptir anlamı taşıyan tablo bilgisine erişmek için kullanılır. |
| EFFECTIVE_END_DATE | DATE | ✓ |  | EFFECTIVE_START_DATE ile EFFECTIVE_END_DATE arasında kullanıcının PREPAID_BALANCE ve CURRENT_STATE'e sahip olduğunu, bu tarihte kullanıcının bu iki bilgisinden birinin değiştiği için farklı bir STATE yada BALANCE'a geçtiğini belirtir. Yeni bilgi, yeni EFFECTIVE_START_DATE olarak farklı bir satırda mevcut olur. |
| CURRENT_STATE | VARCHAR2 | ✓ |  | ACTIVE,DISABLE,GRACE olarak değerler alıp, kullanıcının PREPAID lifecycle döngüsünde hangi aşamada olduğunu belirtir. |
| PREPAID_BALANCE | VARCHAR2 | ✓ |  | Kullanıcın, hesabında bulunan bakiye. |
| DIM_HASH | RAW | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| REVOKE_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| REVOKE_PI_ID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| PREPAID_EFFECTIVE_END_DATE | DATE | ✓ |  | Kullanıcı eğer PREPAID'den POSTPAID'e geçtiyse geçiş tarihini belirtir ve kullanıcının EFFECTIVE_START_DATE, EFFECTIVE_END_DATE tarihleri arasındaki bilgisinin bu tarihten sonra geçersiz olduğunu gösterir. |
| LIFECYCLE_EFFECTIVE_END_DATE | DATE | ✓ |  | Kullanıcı eğer CHURN olduysa, CHURN tarihini belirittir, ve kullanıcının EFFECTIVE_START_DATE, EFFECTIVE_END_DATE tarihleri arasındaki bilgisinin bu tarihten sonra geçersiz olduğunu gösterir. |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.300064+00:00*

- **CURRENT_STATE**: `ACTIVE`, `DISABLE`, `GRACE`, `IDLE`, `POOL`
- **PREPOST_PAID**: `PREP`

<!-- ARIA:ENUM-VALUES-END -->
