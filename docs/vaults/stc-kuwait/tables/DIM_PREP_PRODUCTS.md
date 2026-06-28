---
table: DIM_PREP_PRODUCTS
database: oracle
workspace: stc-kuwait
keywords: [bundle, faturasız, offer, package, packages, paket, plan, prepaid, product,
  tariff, without invoice]
generated_at: '2026-06-16T03:23:43.168051+00:00'
enriched_at: '2026-06-28T11:02:01.460133+00:00'
description: Dimension table that holds the features, quotas and prices of prepaid
  products, packages, tariffs and add-ons.
---

# DIM_PREP_PRODUCTS

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

## Relationships

- `OFFER_ID` → `FCT_PREP_MASTER.OFFER_ID` (foreign_key)
- `OFFER_ID` → `FCT_PREP_PROVISION.OFFER_ID` (foreign_key)
- `OFFER_ID` → `FCT_PREP_RECHARGE.OFFER_ID` (foreign_key)
- `OFFER_ID` → `FCT_PREP_REV.OFFER_ID` (foreign_key)
- `OFFER_ID` → `FCT_PREP_ROAMING.OFFER_ID` (foreign_key)
- `OFFER_ID` → `FCT_PREP_USAGE.OFFER_ID` (foreign_key)
- `PROD_OFFERING_ID` → `FCT_PREP_MASTER.PROD_OFFERING_ID` (foreign_key)
- `EQUIPID` → `FCT_PREP_PROVISION.EQUIPID` (foreign_key)
## Business Metadata

