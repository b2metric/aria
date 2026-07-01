---
table: FCT_PREP_PROVISION
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, bandwidth, batch, billing, bundle, channel, contract, country, customer, data, date, demographic, etl, financial, geography, income, internet, lifecycle, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, service, snapshot, state, status, subscriber, subscription, tariff, temporal, time, touchpoint, usage]
description: "Fact table containing transactional/event data for Prep Provision"
row_count: 118114417
generated_at: 2026-07-01T22:24:18.304789+00:00
---

# FCT_PREP_PROVISION

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
| PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonları, veyahut ürün tipleri değişiyorsa (Örneğin IPHONE 16'ının renk / GB kombinasyonları ), buna tek bir PROD_OFFERING_ID atanır, bu ürün grubunun içerisindeki farklı ürünlere farklı OFFER_ID'ler atanır. |
| PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle' |
| PRODUCT_TYPE | VARCHAR2 | ✓ |  | AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar. |
| OFFER_ID | VARCHAR2 | ✓ |  | CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında, provision'a ait telekom ürün kotaları, ürünün özellikleri bu ID ile erişilebilir. |
| PR_ID | VARCHAR2 | ✓ |  | TechnoTree'de tekil bir ürüne atanan ürün tanımlayıcısı. Bu ürün tanımlayıcısıyla ürünün diğer bilgilerine (attribute) erişmek mümkün. Yenilemeli ürünse, ilk başlatıldığı tarih, ve sona erdiği tarih, cihaz ise renk, kapasite gibi detaylar FCT_SUBS_PROVISION da her PR_ID için attribute kırılımlarına erişilebilir. Örneğin, sistemde kullanıcı insiyatifiyle başlatılan 10000 ürün varsa, 100000 PR_ID bulunmak zorundadır. Tek istisna, aynı ürünün birden çok ürünle kombine edildiği BUNDLE ürün olması durumudur. BUNDLE durumunda, bir PR_ID bir ürün grubu için (aksesuar, telefon, kılıf) atanabilir, bu durumda tekilleştirme PR_ID ve IMEI birleştirerek yapılır. |
| SERVICETYPE | VARCHAR2 | ✓ |  | Önemsiz kullanılmaması gerekir. |
| EQUIPID | VARCHAR2 | ✓ |  | PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında kullanılan tanımlayıcı, PREBUN52 gibi tanımlayıcılar alır. |
| LOGDATE | DATE | ✓ |  | Log kaydının oluşturulduğu tarih/zaman damgası |
| ORDERSTATUS | VARCHAR2 | ✓ |  | Sipariş/işlem durumu (başarılı, başarısız, beklemede, iptal vb.) |
| TRIGGERMODE | VARCHAR2 | ✓ |  | İşlemin tetiklenme şekli (manuel, otomatik, kampanya, sistem tetiklemeli vb.) |
| SOURCE_FLAG | VARCHAR2 | ✓ |  | Provizyon'ın geldiği sistem. — işlemin hangi sistem/kaynak tarafından üretildiğini gösteren işaret. Önemsiz kullanılmaması gerekir. |
| BILLCYCLEID | DATE | ✓ |  | Faturalama döngüsü ID'si, tarih formatında, döngünün ay cinsinden tipini verir. |
| CYCLETYPE | VARCHAR2 | ✓ |  | Önemsiz kullanılmaması gerekir. |
| CYCLELENGTH | VARCHAR2 | ✓ |  | Döngü uzunluğu (örneğin 30 gün, 7 gün) |
| ELAPSECYCLES | VARCHAR2 | ✓ |  | Tamamlanmış/geçmiş döngü sayısı, aynı ürün için geçmişteki döngüler, eğer aynı paketle uzun süre yenileyerek devam ediyor ise. |
| TOTALCYCLES | VARCHAR2 | ✓ |  | Önemsiz kullanılmaması gerekir. |
| CYCLEBEGINTIME | DATE | ✓ |  | Mevcut döngünün başlangıç zamanı |
| CYCLEENDTIME | DATE | ✓ |  | Mevcut döngünün bitiş zamanı |
| INNERCYCLEBEGINTIME | DATE | ✓ |  | Önemsiz kullanılmaması gerekir. |
| INNERCYCLEENDTIME | DATE | ✓ |  | Önemsiz kullanılmaması gerekir. |
| BILLAMOUNT | NUMBER | ✓ |  | Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir. |
| PAYTYPE | VARCHAR2 | ✓ |  | Önemsiz kullanılmaması gerekir. |
| PREPAIDBALANCE | NUMBER | ✓ |  | İşlem anındaki ön ödemeli bakiye tutarı |
| RELIED_ON_PRID | VARCHAR2 | ✓ |  | Bağlı olunan ürünün (Ana plan) PR_ID'si (referans paket) |
| RELIED_SERVICE_START_DATE | DATE | ✓ |  | Bağlı olunan servisin (Ana plan) başlangıç tarihi |
| RELIED_SERVICE_END_DATE | DATE | ✓ |  | Bağlı olunan servisin (Ana plan) bitiş tarihi |
| RELIED_EQUIPID | VARCHAR2 | ✓ |  | Bağlı olunan ürünün (Ana plan) EQUIPID'si. |
| RELIED_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Bağlı olunan ürünün (Ana plan) teklif (product offering) ID'si |
| RELIED_OFFER_ID | VARCHAR2 | ✓ |  | Bağlı olunan ürünün (Ana plan) offer ID'si |
| RELIED_PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Bağlı olunan ürünün (Ana plan) adı |
| RELIED_RENTAL | NUMBER | ✓ |  | Bağlı olunan ürünün provisionu karşılığında kullanıcıdan çekilen KD miktarını belirtir. |
| CDR_PRODUCTSERIAL | VARCHAR2 | ✓ |  | CDR kaydındaki ürün seri numarası — işlemi CDR ile eşleştirmek için kullanılır |
| CDR_SERIALNO | VARCHAR2 | ✓ |  | CDR seri numarası — kullanım kaydının benzersiz takip numarası |
| CHANNEL_NAME | VARCHAR2 | ✓ |  | İşlemin yapıldığı kanal adı (USSD, IVR, mobil uygulama, web, bayi, çağrı merkezi vb.) |
| ACCOUNTTYPE_REF_COMBINATION | VARCHAR2 | ✓ |  | Hesap tipi referans kombinasyonu — paketin etkilediği bakiye/hesap tipi gruplarının kombinasyonu (örn. ana bakiye, bonus bakiye, data hesabı sınırı kombinasyonları) |
| TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Smart Payment, Dealer USSD, Auto Payment gibi ACCOUNTYPE kurallarından türeyen provizyon tipini gösterir, SMART_PAYMENT|AUTO_PAYMENT gibi | ile ayrılmış işlem kombinasyonu değerleri alır, aynı anda birden çok provizyon tipi olabildiği için. |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.305088+00:00*

- **BS_TYPE**: `DATA`, `VOICE`
- **CHANNEL_NAME**: `3PP`, `B2BWEB`, `CBS`, `CHATBOT`, `CMS`, `CNLVAS`, `DCLM`, `DCLMBULK`, `DMPOS`, `ESTORAPP`, `ESTORAPPNEW`, `ESTORWEB`, `ESTORWEBNEW`, `IVR`, `MOBAPP`, `SMS`, `SPPOS`, `TABS`, `WEB`
- **CYCLELENGTH**: `0`, `1`, `10`, `11`, `12`, `14`, `168`, `180`, `2`, `20`, `28`, `3`, `30`, `336`, `360`, `365`, `420`, `45`, `480`, `5`, `60`, `7`, `8`, `84`, `90`
- **CYCLETYPE**: `-1`, `1`, `2`, `4`, `6`
- **ORDERSTATUS**: `0`, `1`, `3`
- **PAYTYPE**: `0`, `2`
- **PREPOST_PAID**: `POST`, `PREP`
- **PRODUCT_TYPE**: `5GEnabler`, `Accesory`, `AddOns`, `Bonus`, `Boosters`, `Bundles`, `CLMDiscountOffer`, `Commitment Benefit`, `Device`, `DeviceCare`, `DiscountOffer`, `Enablers`, `Fee`, `FiberAddOns`, `FiberPlan`, `Freebies`, `Gift`, `LoyaltyCatalog`, `MainPlan`, `NoSubsidy Commitment`, `Offer`, `PARTNER`, `Refinance`, `Renewal`, `Roaming Access`, `RoamingBundle`, `RoamingLandingPage`, `VASService`
- **SERVICETYPE**: `33`
- **TOTALCYCLES**: `1`, `1000`, `10000`, `4`
- **TRANSACTION_TYPE**: `AUTO_RENEWAL`, `AUTO_RENEWAL|DEALER`, `AUTO_RENEWAL|DEALER_USSD`, `AUTO_RENEWAL|DEALER_USSD|SMART_PAYMENT`, `AUTO_RENEWAL|DEALER_USSD|USER_USSD`, `AUTO_RENEWAL|DEALER|SMART_PAYMENT`, `AUTO_RENEWAL|SMART_PAYMENT`, `AUTO_RENEWAL|USER`, `AUTO_RENEWAL|USER_USSD`, `DEALER_USSD`, `DEALER_USSD|SMART_PAYMENT`, `DEALER_USSD|SMART_PAYMENT|USER_USSD`, `DEALER|SMART_PAYMENT`, `SMART_PAYMENT`, `SMART_PAYMENT|USER`, `SMART_PAYMENT|USER_USSD`, `USER`
- **TRIGGERMODE**: `0`, `1`, `2`, `3`, `4`, `7`, `8`, `A`, `D`, `F`

<!-- ARIA:ENUM-VALUES-END -->
