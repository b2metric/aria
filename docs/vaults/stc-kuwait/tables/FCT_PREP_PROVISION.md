---
table: FCT_PREP_PROVISION
database: oracle
workspace: stc-kuwait
keywords: [activation, membership, opt-in, package pickup, paket alımı, prepaid, provision,
  subscription, üyelik]
generated_at: '2026-06-16T03:23:43.169377+00:00'
enriched_at: '2026-06-16T14:59:52.299288+00:00'
description: Fact table that records package, tariff or service membership (provisioning),
  activation and cancellation transactions of prepaid subscribers.
---

# FCT_PREP_PROVISION

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
 | PROD_OFFERING_ID | VARCHAR2 | ✓ |  | If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group. | 
 | PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle' | 
 | PRODUCT_TYPE | VARCHAR2 | ✓ |  | Stores the categorization of product groups such as AddOn, Bundle, Device. | 
 | OFFER_ID | NUMBER | ✓ |  | The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID. | 
 | PR_ID | NUMBER | ✓ |  | Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI. | 
 | SERVICETYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | EQUIPID | VARCHAR2 | ✓ |  | Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52. | 
 | LOGDATE | DATE | ✓ |  | Date/time stamp when the log record was created | 
 | ORDERSTATUS | VARCHAR2 | ✓ |  | Order/transaction status (successful, failed, pending, cancelled, etc.) | 
 | TRIGGERMODE | VARCHAR2 | ✓ |  | How the action is triggered (manual, automatic, campaign, system triggered, etc.) | 
 | SOURCE_FLAG | VARCHAR2 | ✓ |  | The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily. | 
 | BILLCYCLEID | VARCHAR2 | ✓ |  | The billing cycle ID gives the type of cycle in months, in date format. | 
 | CYCLETYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | CYCLELENGTH | NUMBER | ✓ |  | Cycle length (e.g. 30 days, 7 days) | 
 | ELAPSECYCLES | NUMBER | ✓ |  | Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time. | 
 | TOTALCYCLES | NUMBER | ✓ |  | It should not be used unnecessarily. | 
 | CYCLEBEGINTIME | DATE | ✓ |  | Start time of the current cycle | 
 | CYCLEENDTIME | DATE | ✓ |  | End time of the current cycle | 
 | INNERCYCLEBEGINTIME | DATE | ✓ |  | It should not be used unnecessarily. | 
 | INNERCYCLEENDTIME | DATE | ✓ |  | It should not be used unnecessarily. | 
 | BILLAMOUNT | NUMBER | ✓ |  | It indicates the amount of KD withdrawn from the user in return for the provision. | 
 | PAYTYPE | VARCHAR2 | ✓ |  | It should not be used unnecessarily. | 
 | PREPAIDBALANCE | NUMBER | ✓ |  | Prepaid balance amount at the time of transaction | 
 | RELIED_ON_PRID | VARCHAR2 | ✓ |  | PR_ID (reference package) of the connected product (Main plan) | 
 | RELIED_SERVICE_START_DATE | DATE | ✓ |  | Start date of the connected service (Main plan) | 
 | RELIED_SERVICE_END_DATE | DATE | ✓ |  | End date of the connected service (Main plan) | 
 | RELIED_EQUIPID | VARCHAR2 | ✓ |  | EQUIPID of the dependent product (Master plan). | 
 | RELIED_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Product offering ID of the connected product (Main plan) | 
 | RELIED_OFFER_ID | VARCHAR2 | ✓ |  | Offer ID of the connected product (Main plan) | 
 | RELIED_PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Name of the linked product (Main plan) | 
 | RELIED_RENTAL | NUMBER | ✓ |  | It indicates the amount of KD withdrawn from the user in return for the provision of the connected product. | 
 | CDR_PRODUCTSERIAL | VARCHAR2 | ✓ |  | Product serial number in the CDR record — used to match the transaction to the CDR | 
 | CDR_SERIALNO | VARCHAR2 | ✓ |  | CDR serial number — unique tracking number of the usage record | 
 | CHANNEL_NAME | VARCHAR2 | ✓ |  | Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.) | 
 | ACCOUNTTYPE_REF_COMBINATION | VARCHAR2 | ✓ |  | Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations) | 
 | TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT | AUTO_PAYMENT gibi | Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT | AUTO_PAYMENT gibi | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​​​​separated by , since there can be more than one provision type at the same time. | 

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
- **PROD_OFFERING_ID**: 
- **PRODUCT_OFFER_NAME**: 
- **PRODUCT_TYPE**: 
- **OFFER_ID**: 
- **PR_ID**: 
- **SERVICETYPE**: 
- **EQUIPID**: 
- **LOGDATE**: 
- **ORDERSTATUS**: 
- **TRIGGERMODE**: 
- **SOURCE_FLAG**: 
- **BILLCYCLEID**: 
- **CYCLETYPE**: 
- **CYCLELENGTH**: 
- **ELAPSECYCLES**: 
- **TOTALCYCLES**: 
- **CYCLEBEGINTIME**: 
- **CYCLEENDTIME**: 
- **INNERCYCLEBEGINTIME**: 
- **INNERCYCLEENDTIME**: 
- **BILLAMOUNT**: 
- **PAYTYPE**: 
- **PREPAIDBALANCE**: 
- **RELIED_ON_PRID**: 
- **RELIED_SERVICE_START_DATE**: 
- **RELIED_SERVICE_END_DATE**: 
- **RELIED_EQUIPID**: 
- **RELIED_PROD_OFFERING_ID**: 
- **RELIED_OFFER_ID**: 
- **RELIED_PRODUCT_OFFER_NAME**: 
- **RELIED_RENTAL**: 
- **CDR_PRODUCTSERIAL**: 
- **CDR_SERIALNO**: 
- **CHANNEL_NAME**: 
- **ACCOUNTTYPE_REF_COMBINATION**: 
- **TRANSACTION_TYPE**:
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
- **PROD_OFFERING_ID**: Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonları, veyahut ürün tipleri değişiyorsa (Örneğin IPHONE 16'ının renk / GB kombinasyonları ), buna tek bir PROD_OFFERING_ID atanır, bu ürün grubunun içerisindeki farklı ürünlere farklı OFFER_ID'ler atanır.
- **PRODUCT_OFFER_NAME**: Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar.
- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında, provision'a ait telekom ürün kotaları, ürünün özellikleri bu ID ile erişilebilir.
- **PR_ID**: TechnoTree'de tekil bir ürüne atanan ürün tanımlayıcısı. Bu ürün tanımlayıcısıyla ürünün diğer bilgilerine (attribute) erişmek mümkün. Yenilemeli ürünse, ilk başlatıldığı tarih, ve sona erdiği tarih, cihaz ise renk, kapasite gibi detaylar FCT_SUBS_PROVISION da her PR_ID için attribute kırılımlarına erişilebilir. Örneğin, sistemde kullanıcı insiyatifiyle başlatılan 10000 ürün varsa, 100000 PR_ID bulunmak zorundadır. Tek istisna, aynı ürünün birden çok ürünle kombine edildiği BUNDLE ürün olması durumudur. BUNDLE durumunda, bir PR_ID bir ürün grubu için (aksesuar, telefon, kılıf) atanabilir, bu durumda tekilleştirme PR_ID ve IMEI birleştirerek yapılır.
- **SERVICETYPE**: Önemsiz kullanılmaması gerekir.
- **EQUIPID**: PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında kullanılan tanımlayıcı, PREBUN52 gibi tanımlayıcılar alır.
- **LOGDATE**: Log kaydının oluşturulduğu tarih/zaman damgası
- **ORDERSTATUS**: Sipariş/işlem durumu (başarılı, başarısız, beklemede, iptal vb.)
- **TRIGGERMODE**: İşlemin tetiklenme şekli (manuel, otomatik, kampanya, sistem tetiklemeli vb.)
- **SOURCE_FLAG**: Provizyon'ın geldiği sistem. — işlemin hangi sistem/kaynak tarafından üretildiğini gösteren işaret. Önemsiz kullanılmaması gerekir.
- **BILLCYCLEID**: Faturalama döngüsü ID'si, tarih formatında, döngünün ay cinsinden tipini verir.
- **CYCLETYPE**: Önemsiz kullanılmaması gerekir.
- **CYCLELENGTH**: Döngü uzunluğu (örneğin 30 gün, 7 gün)
- **ELAPSECYCLES**: Tamamlanmış/geçmiş döngü sayısı, aynı ürün için geçmişteki döngüler, eğer aynı paketle uzun süre yenileyerek devam ediyor ise.
- **TOTALCYCLES**: Önemsiz kullanılmaması gerekir.
- **CYCLEBEGINTIME**: Mevcut döngünün başlangıç zamanı
- **CYCLEENDTIME**: Mevcut döngünün bitiş zamanı
- **INNERCYCLEBEGINTIME**: Önemsiz kullanılmaması gerekir.
- **INNERCYCLEENDTIME**: Önemsiz kullanılmaması gerekir.
- **BILLAMOUNT**: Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir.
- **PAYTYPE**: Önemsiz kullanılmaması gerekir.
- **PREPAIDBALANCE**: İşlem anındaki ön ödemeli bakiye tutarı
- **RELIED_ON_PRID**: Bağlı olunan ürünün (Ana plan) PR_ID'si (referans paket)
- **RELIED_SERVICE_START_DATE**: Bağlı olunan servisin (Ana plan) başlangıç tarihi
- **RELIED_SERVICE_END_DATE**: Bağlı olunan servisin (Ana plan) bitiş tarihi
- **RELIED_EQUIPID**: Bağlı olunan ürünün (Ana plan) EQUIPID'si.
- **RELIED_PROD_OFFERING_ID**: Bağlı olunan ürünün (Ana plan) teklif (product offering) ID'si
- **RELIED_OFFER_ID**: Bağlı olunan ürünün (Ana plan) offer ID'si
- **RELIED_PRODUCT_OFFER_NAME**: Bağlı olunan ürünün (Ana plan) adı
- **RELIED_RENTAL**: Bağlı olunan ürünün provisionu karşılığında kullanıcıdan çekilen KD miktarını belirtir.
- **CDR_PRODUCTSERIAL**: CDR kaydındaki ürün seri numarası — işlemi CDR ile eşleştirmek için kullanılır
- **CDR_SERIALNO**: CDR seri numarası — kullanım kaydının benzersiz takip numarası
- **CHANNEL_NAME**: İşlemin yapıldığı kanal adı (USSD, IVR, mobil uygulama, web, bayi, çağrı merkezi vb.)
- **ACCOUNTTYPE_REF_COMBINATION**: Hesap tipi referans kombinasyonu — paketin etkilediği bakiye/hesap tipi gruplarının kombinasyonu (örn. ana bakiye, bonus bakiye, data hesabı sınırı kombinasyonları)
- **TRANSACTION_TYPE**: Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT|AUTO_PAYMENT gibi | ile ayrılmış işlem kombinasyonu değerleri alır, aynı anda birden çok provizyon tipi olabildiği için.
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
- **PROD_OFFERING_ID**: Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonları, veyahut ürün tipleri değişiyorsa (Örneğin IPHONE 16'ının renk / GB kombinasyonları ), buna tek bir PROD_OFFERING_ID atanır, bu ürün grubunun içerisindeki farklı ürünlere farklı OFFER_ID'ler atanır.
- **PRODUCT_OFFER_NAME**: Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar.
- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında, provision'a ait telekom ürün kotaları, ürünün özellikleri bu ID ile erişilebilir.
- **PR_ID**: TechnoTree'de tekil bir ürüne atanan ürün tanımlayıcısı. Bu ürün tanımlayıcısıyla ürünün diğer bilgilerine (attribute) erişmek mümkün. Yenilemeli ürünse, ilk başlatıldığı tarih, ve sona erdiği tarih, cihaz ise renk, kapasite gibi detaylar FCT_SUBS_PROVISION da her PR_ID için attribute kırılımlarına erişilebilir. Örneğin, sistemde kullanıcı insiyatifiyle başlatılan 10000 ürün varsa, 100000 PR_ID bulunmak zorundadır. Tek istisna, aynı ürünün birden çok ürünle kombine edildiği BUNDLE ürün olması durumudur. BUNDLE durumunda, bir PR_ID bir ürün grubu için (aksesuar, telefon, kılıf) atanabilir, bu durumda tekilleştirme PR_ID ve IMEI birleştirerek yapılır.
- **SERVICETYPE**: Önemsiz kullanılmaması gerekir.
- **EQUIPID**: PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında kullanılan tanımlayıcı, PREBUN52 gibi tanımlayıcılar alır.
- **LOGDATE**: Log kaydının oluşturulduğu tarih/zaman damgası
- **ORDERSTATUS**: Sipariş/işlem durumu (başarılı, başarısız, beklemede, iptal vb.)
- **TRIGGERMODE**: İşlemin tetiklenme şekli (manuel, otomatik, kampanya, sistem tetiklemeli vb.)
- **SOURCE_FLAG**: Provizyon'ın geldiği sistem. — işlemin hangi sistem/kaynak tarafından üretildiğini gösteren işaret. Önemsiz kullanılmaması gerekir.
- **BILLCYCLEID**: Faturalama döngüsü ID'si, tarih formatında, döngünün ay cinsinden tipini verir.
- **CYCLETYPE**: Önemsiz kullanılmaması gerekir.
- **CYCLELENGTH**: Döngü uzunluğu (örneğin 30 gün, 7 gün)
- **ELAPSECYCLES**: Tamamlanmış/geçmiş döngü sayısı, aynı ürün için geçmişteki döngüler, eğer aynı paketle uzun süre yenileyerek devam ediyor ise.
- **TOTALCYCLES**: Önemsiz kullanılmaması gerekir.
- **CYCLEBEGINTIME**: Mevcut döngünün başlangıç zamanı
- **CYCLEENDTIME**: Mevcut döngünün bitiş zamanı
- **INNERCYCLEBEGINTIME**: Önemsiz kullanılmaması gerekir.
- **INNERCYCLEENDTIME**: Önemsiz kullanılmaması gerekir.
- **BILLAMOUNT**: Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir.
- **PAYTYPE**: Önemsiz kullanılmaması gerekir.
- **PREPAIDBALANCE**: İşlem anındaki ön ödemeli bakiye tutarı
- **RELIED_ON_PRID**: Bağlı olunan ürünün (Ana plan) PR_ID'si (referans paket)
- **RELIED_SERVICE_START_DATE**: Bağlı olunan servisin (Ana plan) başlangıç tarihi
- **RELIED_SERVICE_END_DATE**: Bağlı olunan servisin (Ana plan) bitiş tarihi
- **RELIED_EQUIPID**: Bağlı olunan ürünün (Ana plan) EQUIPID'si.
- **RELIED_PROD_OFFERING_ID**: Bağlı olunan ürünün (Ana plan) teklif (product offering) ID'si
- **RELIED_OFFER_ID**: Bağlı olunan ürünün (Ana plan) offer ID'si
- **RELIED_PRODUCT_OFFER_NAME**: Bağlı olunan ürünün (Ana plan) adı
- **RELIED_RENTAL**: Bağlı olunan ürünün provisionu karşılığında kullanıcıdan çekilen KD miktarını belirtir.
- **CDR_PRODUCTSERIAL**: CDR kaydındaki ürün seri numarası — işlemi CDR ile eşleştirmek için kullanılır
- **CDR_SERIALNO**: CDR seri numarası — kullanım kaydının benzersiz takip numarası
- **CHANNEL_NAME**: İşlemin yapıldığı kanal adı (USSD, IVR, mobil uygulama, web, bayi, çağrı merkezi vb.)
- **ACCOUNTTYPE_REF_COMBINATION**: Hesap tipi referans kombinasyonu — paketin etkilediği bakiye/hesap tipi gruplarının kombinasyonu (örn. ana bakiye, bonus bakiye, data hesabı sınırı kombinasyonları)
- **TRANSACTION_TYPE**: Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT|AUTO_PAYMENT gibi | ile ayrılmış işlem kombinasyonu değerleri alır, aynı anda birden çok provizyon tipi olabildiği için.
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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​separated by , since there can be more than one provision type at the same time.
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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​separated by , since there can be more than one provision type at the same time.
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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​separated by , since there can be more than one provision type at the same time.
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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​separated by , since there can be more than one provision type at the same time.
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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​​​separated by , since there can be more than one provision type at the same time.
## Business Metadata

**Description:** Fact table that records package, tariff or service membership (provisioning), activation and cancellation transactions of prepaid subscribers.

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
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PR_ID**: Product identifier assigned to a unique product in TechnoTree. With this product identifier, it is possible to access other information (attributes) of the product. If it is a product with renewal, the date it was first started and the date it ended, if it is a device, details such as color and capacity can be accessed in FCT_SUBS_PROVISION, attribute breakdowns for each PR_ID. For example, if there are 10000 products launched by user initiative in the system, there must be 100000 PR_IDs. The only exception is a BUNDLE product where the same product is combined with more than one product. In case of BUNDLE, a PR_ID can be assigned for a group of products (accessory, phone, case), in this case deduplication is done by combining PR_ID and IMEI.
- **SERVICETYPE**: It should not be used unnecessarily.
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **LOGDATE**: Date/time stamp when the log record was created
- **ORDERSTATUS**: Order/transaction status (successful, failed, pending, cancelled, etc.)
- **TRIGGERMODE**: How the action is triggered (manual, automatic, campaign, system triggered, etc.)
- **SOURCE_FLAG**: The system where Provision comes from. — flag indicating which system/resource generated the transaction. It should not be used unnecessarily.
- **BILLCYCLEID**: The billing cycle ID gives the type of cycle in months, in date format.
- **CYCLETYPE**: It should not be used unnecessarily.
- **CYCLELENGTH**: Cycle length (e.g. 30 days, 7 days)
- **ELAPSECYCLES**: Number of completed/past cycles, past cycles for the same product, if it continues to be renewed with the same package for a long time.
- **TOTALCYCLES**: It should not be used unnecessarily.
- **CYCLEBEGINTIME**: Start time of the current cycle
- **CYCLEENDTIME**: End time of the current cycle
- **INNERCYCLEBEGINTIME**: It should not be used unnecessarily.
- **INNERCYCLEENDTIME**: It should not be used unnecessarily.
- **BILLAMOUNT**: It indicates the amount of KD withdrawn from the user in return for the provision.
- **PAYTYPE**: It should not be used unnecessarily.
- **PREPAIDBALANCE**: Prepaid balance amount at the time of transaction
- **RELIED_ON_PRID**: PR_ID (reference package) of the connected product (Main plan)
- **RELIED_SERVICE_START_DATE**: Start date of the connected service (Main plan)
- **RELIED_SERVICE_END_DATE**: End date of the connected service (Main plan)
- **RELIED_EQUIPID**: EQUIPID of the dependent product (Master plan).
- **RELIED_PROD_OFFERING_ID**: Product offering ID of the connected product (Main plan)
- **RELIED_OFFER_ID**: Offer ID of the connected product (Main plan)
- **RELIED_PRODUCT_OFFER_NAME**: Name of the linked product (Main plan)
- **RELIED_RENTAL**: It indicates the amount of KD withdrawn from the user in return for the provision of the connected product.
- **CDR_PRODUCTSERIAL**: Product serial number in the CDR record — used to match the transaction to the CDR
- **CDR_SERIALNO**: CDR serial number — unique tracking number of the usage record
- **CHANNEL_NAME**: Channel name where the transaction was made (USSD, IVR, mobile application, web, dealer, call center, etc.)
- **ACCOUNTTYPE_REF_COMBINATION**: Account type reference combination — combination of balance/account type groups affected by the package (e.g. main balance, bonus balance, data account limit combinations)
- **TRANSACTION_TYPE**: Shows the provision type derived from ACCOUNTYPE rules such as Smart Payment, Dealer USSD, Auto Payment, etc. | It takes transaction combination values ​​​​​​​separated by , since there can be more than one provision type at the same time.
