---
table: VW_DAILY_PREP_SUBSCRIPTIONS
database: oracle
workspace: stc-kuwait
keywords: [account, acquisition, activation, batch, billing, bundle, channel, contract, country, customer, date, demographic, etl, financial, geography, income, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, revenue, service, snapshot, subscriber, subscription, tariff, temporal, time, touchpoint]
description: "View aggregating data for Daily Prep Subscriptions"
row_count: 2025
generated_at: 2026-07-01T22:36:31.236497+00:00
---

# VW_DAILY_PREP_SUBSCRIPTIONS

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | ETL execution date |
| TRANSDATE | DATE | ✓ |  | Transdate |
| CONTRNO | VARCHAR2 | ✓ |  | Contract number (subscriber identifier) |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN (phone number) |
| ACTIVATION_DATE | DATE | ✓ |  | Activation Date |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (Individual, Corporate, VIP) |
| NATIONALITY | VARCHAR2 | ✓ |  | Customer nationality |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Prepost Paid |
| BS_TYPE | VARCHAR2 | ✓ |  | Basic service type (Voice, Data, M2M) |
| OFFER_ID | VARCHAR2 | ✓ |  | Offer Id |
| PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Prod Offering Id |
| PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Product Offer Name |
| PROD_ID | VARCHAR2 | ✓ |  | Prod Id |
| PROD_NAME | VARCHAR2 | ✓ |  | Prod Name |
| PRODUCT_BENEFITS | VARCHAR2 | ✓ |  | Product Benefits |
| PRODUCT_TYPE | VARCHAR2 | ✓ |  | Product Type |
| SUB_PRODUCT_TYPE | VARCHAR2 | ✓ |  | Sub Product Type |
| PRODUCT_VALIDITY | VARCHAR2 | ✓ |  | Product Validity |
| PRODUCT_PRICE | VARCHAR2 | ✓ |  | Product Price |
| NEW_RENTAL | NUMBER | ✓ |  | New Rental |
| PREV_LOGDATE | DATE | ✓ |  | Prev Logdate |
| PREV_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Prev Prod Offering Id |
| PREV_PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Prev Product Offer Name |
| PREV_OFFER_ID | VARCHAR2 | ✓ |  | Prev Offer Id |
| OLD_RENTAL | NUMBER | ✓ |  | Old Rental |
| DAYS_SINCE_CHANGE | NUMBER | ✓ |  | Days Since Change |
| NEXT_LOGDATE | DATE | ✓ |  | Next Logdate |
| NEXT_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Next Prod Offering Id |
| NEXT_PRODUCT_OFFER_NAME | VARCHAR2 | ✓ |  | Next Product Offer Name |
| NEXT_OFFER_ID | VARCHAR2 | ✓ |  | Next Offer Id |
| NEXT_RENTAL | NUMBER | ✓ |  | Next Rental |
| DAYS_TO_NEXT_CHANGE | NUMBER | ✓ |  | Days To Next Change |
| PR_ID | VARCHAR2 | ✓ |  | Pr Id |
| EQUIPID | VARCHAR2 | ✓ |  | Equipid |
| TRIGGERMODE | VARCHAR2 | ✓ |  | Triggermode |
| CYCLETYPE | VARCHAR2 | ✓ |  | Cycletype |
| CYCLELENGTH | VARCHAR2 | ✓ |  | Cyclelength |
| ELAPSECYCLES | VARCHAR2 | ✓ |  | Elapsecycles |
| CYCLEBEGINTIME | DATE | ✓ |  | Cyclebegintime |
| CYCLEENDTIME | DATE | ✓ |  | Cycleendtime |
| INNERCYCLEBEGINTIME | DATE | ✓ |  | Innercyclebegintime |
| INNERCYCLEENDTIME | DATE | ✓ |  | Innercycleendtime |
| PAYTYPE | VARCHAR2 | ✓ |  | Paytype |
| PREPAIDBALANCE | NUMBER | ✓ |  | Prepaidbalance |
| LOGDATE | DATE | ✓ |  | Logdate |
| CHANNEL_NAME | VARCHAR2 | ✓ |  | Transaction channel |
| TRANSACTION_CHANNEL | VARCHAR2 | ✓ |  | Transaction Channel |
| TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Transaction Type |
| BILLAMOUNT | NUMBER | ✓ |  | Billed amount (revenue) |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:36:31.236815+00:00*

- **BS_TYPE**: `DATA`, `VOICE`
- **CHANNEL_NAME**: `AUTO_ACTIVATED`, `CBS`, `CMS`, `CRM`, `CUSTOMER_USSD`, `DEALER_USSD`, `DIGITAL`, `IVR`, `OTHERS`, `SMS`
- **CONTRACT_CATEGORY**: `INDIVIDUAL`, `Individual Premium`
- **CYCLELENGTH**: `180`, `28`, `30`, `336`, `365`, `7`, `90`
- **CYCLETYPE**: `-1`, `1`, `2`, `4`, `6`
- **ELAPSECYCLES**: `1`, `10`, `13`, `19`, `22`, `31`, `34`, `41`, `66`, `72`, `94`, `941`, `942`, `952`, `980`, `981`, `994`
- **EQUIPID**: `BON1000ON`, `BON100LM`, `BONUSPR94`, `PO12753AEU`, `PO23083ANT`, `PO39701DID`, `PO44014EMQ`, `PO66075JEF`, `PREBUN281`, `PREBUN282`, `PREBUN283`, `PREBUN284`, `PREBUN285`, `PREBUN286`, `PREBUN5`, `PREDKSA`, `STCGO12MP`, `STCGO3MP`, `STCGO6MP`
- **NATIONALITY**: `BGD`, `EGY`, `IND`, `KWT`, `NPL`, `PHL`, `SDN`, `SYR`
- **NEXT_OFFER_ID**: `271270`, `271271`, `271272`, `271273`, `271274`, `271275`, `271276`, `271277`, `271278`, `271279`, `271280`, `271298`, `280068`, `280069`, `280070`
- **NEXT_PRODUCT_OFFER_NAME**: `Pre KD12 30D PLN`, `Pre KD15.3 3M PLN`, `Pre KD18 195GB 300LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN R`, `Pre KD36 390GB 600LocalMin 6M BUN`, `Pre KD36 390GB 600LocalMin 6M BUN R`, `Pre KD42 450GB 1200LocalMin 6M BUN`, `Pre KD42 450GB 1200LocalMin 6M BUN R`, `Pre KD45 1Y PLN`, `Pre KD72 780GB 1200LocalMin 12M BUN`, `Pre KD72 780GB 1200LocalMin 12M BUN R`, `Pre KD84 900GB 2400LocalMin 12M BUN`, `Pre KD84 900GB 2400LocalMin 12M BUN R`, `Prepaid 5KD Bundle`
- **NEXT_PROD_OFFERING_ID**: `6474ad29954a91296d7663ab`, `6474bfe145a2c78d876cb038`, `648197ec14be78ea9506c119`, `69649704f6f47cb937e7fe61`, `6964ae14884f8ea98ed85691`, `6964b02229452467c4676c2c`, `6964b17d3806a83efb11a1b4`, `6964b347fdeedf73f7203042`, `6964b64ee20001398833d24e`, `6964b96300f7eba5b49b8174`, `6964ba103806a83efb11dd86`, `6964ba7fe629b7e18cd21d5b`, `6964baf829452467c467b94b`, `6964bb7229452467c467bcb6`, `699c15c428e9b81b815305bc`
- **OFFER_ID**: `270403`, `270424`, `271270`, `271271`, `271272`, `271273`, `271274`, `271275`, `271276`, `271277`, `271278`, `271279`, `271280`, `271290`, `271298`, `280068`, `280069`, `280070`, `280089`
- **PAYTYPE**: `0`, `2`
- **PREPOST_PAID**: `POST`, `PREP`
- **PREV_OFFER_ID**: `271270`, `271271`, `271272`, `271273`, `271274`, `271275`, `271276`, `271277`, `271278`, `271279`, `271280`, `271298`, `280068`, `280069`, `280070`
- **PREV_PRODUCT_OFFER_NAME**: `Pre KD12 30D PLN`, `Pre KD15.3 3M PLN`, `Pre KD18 195GB 300LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN R`, `Pre KD36 390GB 600LocalMin 6M BUN`, `Pre KD36 390GB 600LocalMin 6M BUN R`, `Pre KD42 450GB 1200LocalMin 6M BUN`, `Pre KD42 450GB 1200LocalMin 6M BUN R`, `Pre KD45 1Y PLN`, `Pre KD72 780GB 1200LocalMin 12M BUN`, `Pre KD72 780GB 1200LocalMin 12M BUN R`, `Pre KD84 900GB 2400LocalMin 12M BUN`, `Pre KD84 900GB 2400LocalMin 12M BUN R`, `Prepaid 5KD Bundle`
- **PREV_PROD_OFFERING_ID**: `6474ad29954a91296d7663ab`, `6474bfe145a2c78d876cb038`, `648197ec14be78ea9506c119`, `69649704f6f47cb937e7fe61`, `6964ae14884f8ea98ed85691`, `6964b02229452467c4676c2c`, `6964b17d3806a83efb11a1b4`, `6964b347fdeedf73f7203042`, `6964b64ee20001398833d24e`, `6964b96300f7eba5b49b8174`, `6964ba103806a83efb11dd86`, `6964ba7fe629b7e18cd21d5b`, `6964baf829452467c467b94b`, `6964bb7229452467c467bcb6`, `699c15c428e9b81b815305bc`
- **PRODUCT_BENEFITS**: `100 local minutes Bonus`, `1000 stc to stc minutes`, `Go 6-400GB, 1000LM. 500GB for SM/YT 90D`, `Pre KD18 195GB 300LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN`, `Pre KD36 390GB 600LocalMin 6M BUN`, `Pre KD42 450GB 1200LocalMin 6M BUN`, `Pre KD72 780GB 1200LocalMin 12M BUN`, `Pre KD84 900GB 2400LocalMin 12M BUN`
- **PRODUCT_OFFER_NAME**: `100 local minutes Bonus`, `1000 stc to stc minutes`, `Pre 150GB Social BOS`, `Pre KD12 30D PLN`, `Pre KD15.3 3M PLN`, `Pre KD18 195GB 300LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN R`, `Pre KD36 390GB 600LocalMin 6M BUN`, `Pre KD36 390GB 600LocalMin 6M BUN R`, `Pre KD42 450GB 1200LocalMin 6M BUN`, `Pre KD42 450GB 1200LocalMin 6M BUN R`, `Pre KD45 1Y PLN`, `Pre KD72 780GB 1200LocalMin 12M BUN`, `Pre KD72 780GB 1200LocalMin 12M BUN R`, `Pre KD84 900GB 2400LocalMin 12M BUN`, `Pre KD84 900GB 2400LocalMin 12M BUN R`, `Pre net KD9 100GB 150 SocialMedia 30D PLN - KSA`, `Prepaid 5KD Bundle`
- **PRODUCT_PRICE**: `0`, `12`, `18`, `21`, `24`, `36`, `42`, `45`, `5`, `72`, `84`, `9`
- **PRODUCT_TYPE**: `Bonus`, `Bundles`, `RoamingBundle`
- **PRODUCT_VALIDITY**: `180`, `28`, `30`, `336`, `365`, `7`, `90`
- **PROD_ID**: `6351507219db526b1c3035a4`, `635229ecb738fe4e9be364b8`, `6474ad29954a91296d7663ab`, `6474bfe145a2c78d876cb038`, `648197ec14be78ea9506c119`, `67441108ed8f894e2d037b5a`, `69649704f6f47cb937e7fe61`, `6964ae14884f8ea98ed85691`, `6964b02229452467c4676c2c`, `6964b17d3806a83efb11a1b4`, `6964b347fdeedf73f7203042`, `6964b64ee20001398833d24e`, `6964b96300f7eba5b49b8174`, `6964ba103806a83efb11dd86`, `6964ba7fe629b7e18cd21d5b`, `6964baf829452467c467b94b`, `6964bb7229452467c467bcb6`, `69761224f4bd599426ba3dfb`, `699c15c428e9b81b815305bc`
- **PROD_NAME**: `100 local minutes Bonus`, `1000 stc to stc minutes`, `Pre 150GB Social BOS`, `Pre KD12 30D PLN`, `Pre KD15.3 3M PLN`, `Pre KD18 195GB 300LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN`, `Pre KD21 225GB 600LocalMin 3M BUN R`, `Pre KD36 390GB 600LocalMin 6M BUN`, `Pre KD36 390GB 600LocalMin 6M BUN R`, `Pre KD42 450GB 1200LocalMin 6M BUN`, `Pre KD42 450GB 1200LocalMin 6M BUN R`, `Pre KD45 1Y PLN`, `Pre KD72 780GB 1200LocalMin 12M BUN`, `Pre KD72 780GB 1200LocalMin 12M BUN R`, `Pre KD84 900GB 2400LocalMin 12M BUN`, `Pre KD84 900GB 2400LocalMin 12M BUN R`, `Pre net KD9 100GB 150 SocialMedia 30D PLN - KSA`, `Prepaid 5KD Bundle`
- **PROD_OFFERING_ID**: `6351507219db526b1c3035a4`, `635229ecb738fe4e9be364b8`, `6474ad29954a91296d7663ab`, `6474bfe145a2c78d876cb038`, `648197ec14be78ea9506c119`, `67441108ed8f894e2d037b5a`, `69649704f6f47cb937e7fe61`, `6964ae14884f8ea98ed85691`, `6964b02229452467c4676c2c`, `6964b17d3806a83efb11a1b4`, `6964b347fdeedf73f7203042`, `6964b64ee20001398833d24e`, `6964b96300f7eba5b49b8174`, `6964ba103806a83efb11dd86`, `6964ba7fe629b7e18cd21d5b`, `6964baf829452467c467b94b`, `6964bb7229452467c467bcb6`, `69761224f4bd599426ba3dfb`, `699c15c428e9b81b815305bc`
- **PR_ID**: `PR35100384`, `PR35103794`, `PR35104772`, `PREVASJC324519`, `PREVASK97339`, `PREVASKB208343`, `PREVASKB57838`, `PREVASKC110163`, `PREVASKC341535`, `PREVASKD164793`, `PREVASKD92516`, `PREVASMC137761`, `PREVASNB129282`
- **SUB_PRODUCT_TYPE**: `Bonus`, `Bundles`, `Roaming eSIM Bundle`
- **TRANSACTION_CHANNEL**: `3PP`, `B2BWEB`, `CBS`, `CHATBOT`, `CMS`, `CNLVAS`, `DCLM`, `DCLMBULK`, `DMPOS`, `ESTORAPP`, `ESTORAPPNEW`, `ESTORWEB`, `ESTORWEBNEW`, `IVR`, `MOBAPP`, `SMS`, `SPPOS`, `TABS`, `WEB`
- **TRANSACTION_TYPE**: `AUTO_RENEWAL`, `AUTO_RENEWAL|DEALER`, `AUTO_RENEWAL|DEALER_USSD`, `AUTO_RENEWAL|DEALER_USSD|SMART_PAYMENT`, `AUTO_RENEWAL|DEALER_USSD|USER_USSD`, `AUTO_RENEWAL|DEALER|SMART_PAYMENT`, `AUTO_RENEWAL|SMART_PAYMENT`, `AUTO_RENEWAL|USER`, `AUTO_RENEWAL|USER_USSD`, `DEALER_USSD`, `DEALER_USSD|SMART_PAYMENT`, `DEALER_USSD|SMART_PAYMENT|USER_USSD`, `DEALER|SMART_PAYMENT`, `SMART_PAYMENT`, `SMART_PAYMENT|USER`, `SMART_PAYMENT|USER_USSD`, `USER`
- **TRIGGERMODE**: `0`, `1`, `2`, `3`, `4`, `7`, `8`, `A`, `D`, `F`

<!-- ARIA:ENUM-VALUES-END -->
