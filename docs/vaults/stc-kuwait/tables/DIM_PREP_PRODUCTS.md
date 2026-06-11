---
table: DIM_PREP_PRODUCTS
database: oracle
workspace: stc-kuwait
keywords: [billing, bundle, financial, income, money, offer, package, payment, prepaid,
  product, revenue, subscriber, tariff]
generated_at: 2026-06-07 11:22:23.795995+00:00
enriched_at: '2026-06-11T23:16:10.455093+00:00'
---

# DIM_PREP_PRODUCTS

**Description:** Dimension table containing reference/master data for Prep Products

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | OFFER_ID | NUMBER | ✓ |  | CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında a | 
 | PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonlar | 
 | BUSINESS | VARCHAR2 | ✓ |  | Prepaid, Postpaid gibi ürün dikeylerini belitmek için kullanılır. | 
 | PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle' | 
 | EQUIPID | VARCHAR2 | ✓ |  | PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında  | 
 | PRODUCT_BENEFITS | VARCHAR2 | ✓ |  | Serbest metin olarak, bu provision karşılığında kullanıcının belirtilen gün boyunca hangi telekom fa | 
 | PRODUCT_TYPE | VARCHAR2 | ✓ |  | AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar. | 
 | SUB_PRODUCT_TYPE | VARCHAR2 | ✓ |  | Ana ürün grubu, birden fazla alt ürün grubu içeriyorsa, ikincil kategorizasyon hiyerarşisi. | 
 | PRODUCT_VALIDITY | VARCHAR2 | ✓ |  | Ürünün geçerli olduğu, kullanıcının bu tarihten sonra erişiminin sınırlandırılacağı gün sayısını sak | 
 | PRODUCT_PRICE | NUMBER | ✓ |  | Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir. | 

## Keywords

billing, bundle, financial, income, money, offer, package, payment, prepaid, product, revenue, subscriber, tariff
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında, provision'a ait telekom ürün kotaları, ürünün özellikleri bu ID ile erişilebilir.
- **PROD_OFFERING_ID**: Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonları, veyahut ürün tipleri değişiyorsa (Örneğin IPHONE 16'ının renk / GB kombinasyonları ), buna tek bir PROD_OFFERING_ID atanır, bu ürün grubunun içerisindeki farklı ürünlere farklı OFFER_ID'ler atanır.
- **BUSINESS**: Prepaid, Postpaid gibi ürün dikeylerini belitmek için kullanılır.
- **PRODUCT_OFFER_NAME**: Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında kullanılan tanımlayıcı, PREBUN52 gibi tanımlayıcılar alır.
- **PRODUCT_BENEFITS**: Serbest metin olarak, bu provision karşılığında kullanıcının belirtilen gün boyunca hangi telekom faydalarına erişebileceği (GB, VOICE, SMS) ve bunların kombinasyonlarını belirtir. Örneğin 1000 dakika, 50 GB.
- **PRODUCT_TYPE**: AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar.
- **SUB_PRODUCT_TYPE**: Ana ürün grubu, birden fazla alt ürün grubu içeriyorsa, ikincil kategorizasyon hiyerarşisi.
- **PRODUCT_VALIDITY**: Ürünün geçerli olduğu, kullanıcının bu tarihten sonra erişiminin sınırlandırılacağı gün sayısını saklar.
- **PRODUCT_PRICE**: Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir.
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında gelir.
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında gelir
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasındadır
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında gelir.
## Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında adsadad
## Column Descriptions

- **OFFER_ID**: a CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında a
## Business Metadata


### Column Descriptions

- **OFFER_ID**: CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında a
