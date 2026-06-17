---
table: DIM_PREP_PRODUCTS
database: oracle
workspace: stc-kuwait
keywords: [bundle, faturasız, offer, package, packages, paket, plan, prepaid, product,
  tariff, without invoice]
generated_at: '2026-06-16T03:23:43.168051+00:00'
enriched_at: '2026-06-16T14:59:52.292962+00:00'
description: Dimension table that holds the features, quotas and prices of prepaid
  products, packages, tariffs and add-ons.
---

# DIM_PREP_PRODUCTS

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | OFFER_ID | NUMBER | ✓ |  | The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID. | 
 | PROD_OFFERING_ID | VARCHAR2 | ✓ |  | If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group. | 
 | BUSINESS | VARCHAR2 | ✓ |  | It is used to indicate product verticals such as Prepaid and Postpaid. | 
 | PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle' | 
 | EQUIPID | VARCHAR2 | ✓ |  | Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52. | 
 | PRODUCT_BENEFITS | VARCHAR2 | ✓ |  | In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB. | 
 | PRODUCT_TYPE | VARCHAR2 | ✓ |  | Stores the categorization of product groups such as AddOn, Bundle, Device. | 
 | SUB_PRODUCT_TYPE | VARCHAR2 | ✓ |  | Secondary categorization hierarchy if the main product group contains more than one child product group. | 
 | PRODUCT_VALIDITY | VARCHAR2 | ✓ |  | It stores the number of days that the product is valid and the user's access will be limited after this date. | 
 | PRODUCT_PRICE | NUMBER | ✓ |  | It indicates the amount of KD withdrawn from the user in return for the provision. | 

## Keywords

## Column Descriptions
- **OFFER_ID**: 
- **PROD_OFFERING_ID**: 
- **BUSINESS**: 
- **PRODUCT_OFFER_NAME**: 
- **EQUIPID**: 
- **PRODUCT_BENEFITS**: 
- **PRODUCT_TYPE**: 
- **SUB_PRODUCT_TYPE**: 
- **PRODUCT_VALIDITY**: 
- **PRODUCT_PRICE**:
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

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
## Column Descriptions

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
## Column Descriptions

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
## Column Descriptions

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
## Column Descriptions

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
## Business Metadata

**Description:** Dimension table that holds the features, quotas and prices of prepaid products, packages, tariffs and add-ons.

### Column Descriptions

- **OFFER_ID**: The unique identifier that the GIS system gives to a unique subscription package. During each provision, telecom product quotas and product features belonging to the provision can be accessed with this ID.
- **PROD_OFFERING_ID**: If more than one product group corresponds to the product in the same concept, but payment plans, quota variations, or product types change (For example, color / GB combinations of IPHONE 16), a single PROD_OFFERING_ID is assigned to it, and different OFFER_IDs are assigned to different products within this product group.
- **BUSINESS**: It is used to indicate product verticals such as Prepaid and Postpaid.
- **PRODUCT_OFFER_NAME**: Free text version of the meaningful description of the product. For example; '1TB 30D 6KD Prepaid Bundle'
- **EQUIPID**: Similar to PROD_OFFERING_ID but with 6-8 characters, the identifier used to identify pre-TechnoTree product lines takes identifiers such as PREBUN52.
- **PRODUCT_BENEFITS**: In free text, it specifies which telecom benefits (GB, VOICE, SMS) and their combinations the user will have access to during the specified day in exchange for this provision. For example, 1000 minutes, 50 GB.
- **PRODUCT_TYPE**: Stores the categorization of product groups such as AddOn, Bundle, Device.
- **SUB_PRODUCT_TYPE**: Secondary categorization hierarchy if the main product group contains more than one child product group.
- **PRODUCT_VALIDITY**: It stores the number of days that the product is valid and the user's access will be limited after this date.
- **PRODUCT_PRICE**: It indicates the amount of KD withdrawn from the user in return for the provision.
