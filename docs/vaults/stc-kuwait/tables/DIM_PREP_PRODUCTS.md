---
table: DIM_PREP_PRODUCTS
database: oracle
workspace: stc-kuwait
keywords: [billing, bundle, financial, income, money, offer, package, payment, prepaid, product, revenue, subscriber, tariff]
description: "Dimension table containing reference/master data for Prep Products"
row_count: 743
generated_at: 2026-07-01T22:24:18.299165+00:00
---

# DIM_PREP_PRODUCTS

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| OFFER_ID | VARCHAR2 | ✓ |  | CBS sisteminin, tekil bir subscription paketine verdiği tekil tanımlayıcı. Her provision sırasında, provision'a ait telekom ürün kotaları, ürünün özellikleri bu ID ile erişilebilir. |
| PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Birden fazla ürün grubu aynı konseptteki ürüne denk geliyor, fakat ödeme planları, kota varyasyonları, veyahut ürün tipleri değişiyorsa (Örneğin IPHONE 16'ının renk / GB kombinasyonları ), buna tek bir PROD_OFFERING_ID atanır, bu ürün grubunun içerisindeki farklı ürünlere farklı OFFER_ID'ler atanır. |
| BUSINESS | VARCHAR2 | ✓ |  | Prepaid, Postpaid gibi ürün dikeylerini belitmek için kullanılır. |
| PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Ürünün, anlamlı açıklamasının serbest metin hali. Örneğin; '1TB 30D 6KD Prepaid Bundle' |
| EQUIPID | VARCHAR2 | ✓ |  | PROD_OFFERING_ID'ye benzer fakat 6-8 karakterli, TechnoTree öncesi ürün gruplarının tanımlanmasında kullanılan tanımlayıcı, PREBUN52 gibi tanımlayıcılar alır. |
| PRODUCT_BENEFITS | VARCHAR2 | ✓ |  | Serbest metin olarak, bu provision karşılığında kullanıcının belirtilen gün boyunca hangi telekom faydalarına erişebileceği (GB, VOICE, SMS) ve bunların kombinasyonlarını belirtir. Örneğin 1000 dakika, 50 GB. |
| PRODUCT_TYPE | VARCHAR2 | ✓ |  | AddOn, Bundle, Device gibi ürün gruplarının kategorizasyonunu saklar. |
| SUB_PRODUCT_TYPE | VARCHAR2 | ✓ |  | Ana ürün grubu, birden fazla alt ürün grubu içeriyorsa, ikincil kategorizasyon hiyerarşisi. |
| PRODUCT_VALIDITY | VARCHAR2 | ✓ |  | Ürünün geçerli olduğu, kullanıcının bu tarihten sonra erişiminin sınırlandırılacağı gün sayısını saklar. |
| PRODUCT_PRICE | VARCHAR2 | ✓ |  | Provision karşılığında kullanıcıdan çekilen KD miktarını belirtir. |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.299516+00:00*

- **BUSINESS**: `Prepaid`
- **PRODUCT_TYPE**: `AddOns`, `Bonus`, `Boosters`, `Bundles`, `Enablers`, `Freebies`, `LoyaltyCatalog`, `MainPlan`, `RoamingBundle`, `VASService`
- **PRODUCT_VALIDITY**: `0`, `1`, `10`, `14`, `15`, `180`, `2`, `20`, `240`, `28`, `3`, `30`, `32`, `336`, `360`, `365`, `5`, `60`, `7`, `90`
- **SUB_PRODUCT_TYPE**: `AddOns`, `Bonus`, `Boosters`, `Bundles`, `CLM_Bonus`, `CLM_Bundles`, `CLM_IDD_AddOns`, `CLM_RoamingBundle`, `Community_AddOns`, `Community_Bonus`, `Community_Bundles`, `Enablers`, `Freebies`, `IDD_AddOns`, `IDD_Bonus`, `LoyaltyCatalog`, `MainPlan`, `Roaming eSIM Bundle`, `RoamingBundle`, `VASService`, `Validity_Bundle`

<!-- ARIA:ENUM-VALUES-END -->
