---
table: DIM_PREP_STATE_SCD2
database: oracle
workspace: stc-kuwait
keywords: [abone durumu, history, life cycle, lifecycle, prepaid, scd2, state, status,
  subscriber status, tarihçe]
generated_at: '2026-06-16T03:23:43.168650+00:00'
enriched_at: '2026-06-16T14:59:52.294647+00:00'
description: Dimension table that tracks the lifecycle and status changes of prepaid
  subscribers in a historical manner (SCD Type 2).
---

# DIM_PREP_STATE_SCD2

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | System time when bulk load occurs. | 
 | SNAPSHOT_DATE | DATE | ✓ |  | It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN information. | 
 | APPDATE | DATE | ✓ |  | The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back. | 
 | NEXT_APPDATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Constant information throughout the table as PREP. | 
 | EFFECTIVE_START_DATE | DATE | ✓ |  | Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE. | 
 | EFFECTIVE_END_DATE | DATE | ✓ |  | It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE. | 
 | CURRENT_STATE | VARCHAR2 | ✓ |  | It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle. | 
 | PREPAID_BALANCE | NUMBER | ✓ |  | The balance in the user's account. | 
 | DIM_HASH | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | REVOKE_DATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | REVOKE_PI_ID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | PREPAID_EFFECTIVE_END_DATE | DATE | ✓ |  | If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date. | 
 | LIFECYCLE_EFFECTIVE_END_DATE | DATE | ✓ |  | If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date. | 

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **SNAPSHOT_DATE**: 
- **SUBNO**: 
- **APPDATE**: 
- **NEXT_APPDATE**: 
- **PREPOST_PAID**: 
- **EFFECTIVE_START_DATE**: 
- **EFFECTIVE_END_DATE**: 
- **CURRENT_STATE**: 
- **PREPAID_BALANCE**: 
- **DIM_HASH**: 
- **REVOKE_DATE**: 
- **REVOKE_PI_ID**: 
- **PREPAID_EFFECTIVE_END_DATE**: 
- **LIFECYCLE_EFFECTIVE_END_DATE**:
## Column Descriptions

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
## Column Descriptions

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
## Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
## Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
## Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
## Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
## Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
## Business Metadata

**Description:** Dimension table that tracks the lifecycle and status changes of prepaid subscribers in a historical manner (SCD Type 2).

### Column Descriptions

- **EXEC_DATE**: System time when bulk load occurs.
- **SNAPSHOT_DATE**: It is unimportant, it should not be used, it is an auxiliary function for upsert, it is repetitive because the column used in the ON condition of the MERGE INTO statement cannot be used in the UPDATE SET field.
- **SUBNO**: MSISDN information.
- **APPDATE**: The date MSISDN was activated for a user. A number was added in case it could be activated by different people at different times, or the same user could request their old number back.
- **NEXT_APPDATE**: It is unimportant and should not be used.
- **PREPOST_PAID**: Constant information throughout the table as PREP.
- **EFFECTIVE_START_DATE**: Since it is designed as an SCD2 table, one row matches only one person per day, if the BALANCE or prepaid CURRENT_STATE changes, the column will change. It is used to access table information meaning that the relevant person has CURRENT_STATE (ACTIVE, DISABLE, GRACE) and the amount in PREPAID_BALANCE between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE.
- **EFFECTIVE_END_DATE**: It indicates that the user has PREPAID_BALANCE and CURRENT_STATE between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE, and on this date, the user moves to a different STATE or BALANCE because one of these two information has changed. The new information is available on a different line as the new EFFECTIVE_START_DATE.
- **CURRENT_STATE**: It takes values ​​as ACTIVE, DISABLE, GRACE and indicates at which stage the user is in the PREPAID lifecycle.
- **PREPAID_BALANCE**: The balance in the user's account.
- **DIM_HASH**: It is unimportant and should not be used.
- **REVOKE_DATE**: It is unimportant and should not be used.
- **REVOKE_PI_ID**: It is unimportant and should not be used.
- **PREPAID_EFFECTIVE_END_DATE**: If the user switched from PREPAID to POSTPAID, it indicates the transition date and shows that the user's information between EFFECTIVE_START_DATE and EFFECTIVE_END_DATE is invalid after this date.
- **LIFECYCLE_EFFECTIVE_END_DATE**: If the user CHURN, it indicates the CHURN date, and indicates that the user's information between EFFECTIVE_START_DATE, EFFECTIVE_END_DATE is invalid after this date.
