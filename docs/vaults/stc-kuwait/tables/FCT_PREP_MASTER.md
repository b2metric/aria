---
table: FCT_PREP_MASTER
database: oracle
workspace: stc-kuwait
keywords: [360 view, account, acquisition, activation, balance, bandwidth, batch, billing, bundle, call, channel, churn, contract, country, credit, customer, data, date, demographic, etl, financial, geography, income, international, internet, lifecycle, master, message, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, recharge, retention, revenue, roaming, service, sms, snapshot, state, status, subscriber, subscription, tariff, temporal, time, topup, touchpoint, travel, usage, voice]
description: "Fact table containing transactional/event data for Prep Master"
row_count: 2368941
generated_at: 2026-07-01T22:24:18.301431+00:00
---

# FCT_PREP_MASTER

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). |
| SNAPSHOT_DATE | DATE | ✓ |  | Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih. |
| CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır. |
| SUBNO | VARCHAR2 | ✓ |  | MSISDN |
| PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). |
| NEXT_APPDATE | DATE | ✓ |  | Next Appdate |
| ID_NO | VARCHAR2 | ✓ |  | Müşterinin kimlik numarası (residence, pasaport vb.). |
| ID_TYPE | VARCHAR2 | ✓ |  | ID_NO da yer alan tanımlayıcının kategorik tipi. |
| ICC_NUMBER | VARCHAR2 | ✓ |  | SIM kartın fiziksel seri numarası (Integrated Circuit Card ID). |
| IMSI_NUMBER | VARCHAR2 | ✓ |  | Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara. |
| CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). |
| NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). |
| BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. |
| BS_FLAG | VARCHAR2 | ✓ |  | Bs Flag |
| NUM_TYPE | VARCHAR2 | ✓ |  | Num Type |
| RETAILER | VARCHAR2 | ✓ |  | Retailer |
| REGION | VARCHAR2 | ✓ |  | Geographic region |
| MNP_SUB | VARCHAR2 | ✓ |  | Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı. |
| CREDIT_RISK_PROFILE | VARCHAR2 | ✓ |  | Müşterinin kredi risk profili (düşük/orta/yüksek risk). |
| PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace). |
| CHURN_DATE | DATE | ✓ |  | Churn Date |
| MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| MAIN_PLAN_RENTAL | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| MAIN_PLAN_START_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. |
| PREP_BAL_AT_MONTH_START | NUMBER | ✓ |  | İçinde bulunulan ayın başındaki ön ödemeli (prepaid) bakiye tutarı |
| PREP_BAL_AT_PREV_MONTH_START | NUMBER | ✓ |  | Bugün itibarıyla güncel ön ödemeli bakiye tutarı |
| PREP_BAL_AS_OF_TODAY | NUMBER | ✓ |  | Bugün itibarıyla güncel ön ödemeli bakiye tutarı |
| LT_LAST_ACTIVITY_DT | DATE | ✓ |  | Hat üzerinde gerçekleşen son herhangi bir aktivitenin tarihi |
| LT_LAST_DATA_DT | DATE | ✓ |  | Son mobil veri (internet) kullanım tarihi |
| LT_LAST_VOICE_OUTGOING_DT | DATE | ✓ |  | Son giden sesli arama tarihi |
| LT_LAST_VOICE_INCOMING_DT | DATE | ✓ |  | Son gelen sesli arama tarihi |
| LT_LAST_SMS_OUTGOING_DT | DATE | ✓ |  | Son giden SMS tarihi |
| LT_LAST_RECHARGE_DT | DATE | ✓ |  | Son TL yükleme (kontör/bakiye yükleme) tarihi |
| LT_LAST_ROAMING_DT | DATE | ✓ |  | Son uluslararası dolaşım (roaming) kullanım tarihi |
| LT_LAST_REVENUE_DT | DATE | ✓ |  | STC'e gelir yaratan son işlemin tarihi |
| LT_LAST_SGWCDR_ACTIVITY_DT | DATE | ✓ |  | SGW (Serving Gateway) CDR kayıtlarına göre son veri aktivite tarihi (data oturumu bazlı) |
| LT_LAST_PAID_SUBSCRIPTION_DT | DATE | ✓ |  | Son ücretli abonelik/paket satın alma tarihi |
| LT_LAST_BUNDLE_PR_ID | VARCHAR2 | ✓ |  | Son alınan paketin ürün (product) ID'si |
| LT_LAST_BUNDLE_OFFER_ID | VARCHAR2 | ✓ |  | Son alınan paketin teklif (offer) ID'si |
| LT_LAST_BUNDLE_OFFER_NAME | VARCHAR2 | ✓ |  | Son alınan paketin adı |
| LT_LAST_BUNDLE_VALIDIY | VARCHAR2 | ✓ |  | Son alınan paketin geçerlilik süresi |
| LT_LAST_BUNDLE_PRICE | VARCHAR2 | ✓ |  | Son alınan paketin fiyatı |
| LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Son paketin aktive edildiği kanal (USSD, IVR, web, uygulama, bayi vb.) |
| LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | Paketin tetiklenme şekli (manuel, otomatik yenileme, kampanya vb.) |
| LT_LAST_BUNDLE_TRANSACTION_TYPE | VARCHAR2 | ✓ |  | Paket işlem tipi (ilk alım, yenileme, upgrade vb.) |
| LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Paketin sisteme tanımlanma (provisioning) tarihi |
| LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Paket döngüsünün bitiş zamanı |
| LT_LAST_BUNDLE_ELAPSECYCLES | VARCHAR2 | ✓ |  | Paketin kaç döngü/periyot kullanıldığı |
| LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Paketin sonlandırılma tarihi |
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB | NUMBER | ✓ |  | Paketin yurt içi mobil veri kotası (MB) |
| LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | Paketin yurt dışı (roaming) veri kotası (MB) |
| LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Paket kapsamındaki ücretsiz/bedava veri miktarı (MB) |
| LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN | NUMBER | ✓ |  | Yurt içi şebeke içi (aynı operatör) konuşma dakikası |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN | NUMBER | ✓ |  | Yurt içi şebeke dışı (diğer operatörler) konuşma dakikası |
| LT_LAST_BUNDLE_VOICE_ALL_NET_MIN | NUMBER | ✓ |  | Tüm yurt içi şebekelere (on-net + off-net) toplam konuşma dakikası |
| LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN | NUMBER | ✓ |  | Uluslararası arama (yurt dışını arama) dakikası |
| LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN | NUMBER | ✓ |  | Şebeke içi ücretsiz konuşma dakikası |
| LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN | NUMBER | ✓ |  | Şebeke dışı ücretsiz konuşma dakikası |
| LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN | NUMBER | ✓ |  | Şebekeler arası ücretsiz konuşma dakikası (intercall — operatörler arası) |
| LT_LAST_BUNDLE_ROAMING_VOICE_MIN | NUMBER | ✓ |  | Yurt dışı dolaşımda konuşma dakikası |
| LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Yurt içi SMS adedi |
| LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Tüm şebekelere toplam SMS adedi |
| LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Uluslararası SMS adedi |
| LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Yurt dışı dolaşımda SMS adedi |
| ACTV_ADDONS | VARCHAR2 | ✓ |  | Aktif ek paket (add-on) servisleri |
| ACTV_BONUS | VARCHAR2 | ✓ |  | Actv Bonus |
| ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Aktif katma değerli servisler (VAS — Value Added Services; örn. ringback tone, içerik servisleri) |
| ACTV_BOOSTERS | VARCHAR2 | ✓ |  | Actv Boosters |
| ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Aktif yurt dışı dolaşım paketleri |
| ACTV_ENABLERS | VARCHAR2 | ✓ |  | Actv Enablers |
| ACTV_BUNDLES | VARCHAR2 | ✓ |  | Aktif ana paketler |
| ACTV_LOYALTYCATALOG | VARCHAR2 | ✓ |  | Actv Loyaltycatalog |
| ACTV_FREEBIES | VARCHAR2 | ✓ |  | Aktif ücretsiz/hediye servisler |
| ACTV_MAINPLAN | VARCHAR2 | ✓ |  | Actv Mainplan |
| L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 1 günde gelir üreten aktiviteye sahip mi? |
| L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 7 günde gelir üreten aktiviteye sahip mi? |
| L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 15 günde gelir üreten aktiviteye sahip mi? |
| L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 30 günde gelir üreten aktiviteye sahip mi? |
| L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 90 günde gelir üreten aktiviteye sahip mi? |
| L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 120 günde gelir üreten aktiviteye sahip mi? |
| MTD_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Mtd Is Revenue Active Base |
| L1D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 1 günde aktif baz içinde mi? |
| L7D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 7 günde aktif baz içinde mi? |
| L15D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 15 günde aktif baz içinde mi? |
| L30D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 30 günde aktif baz içinde mi? |
| L90D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 90 günde aktif baz içinde mi? |
| L120D_IS_ACTIVE_BASE | NUMBER | ✓ |  | Son 120 günde aktif baz içinde mi? |
| L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 1 gündeki aktivite kaynakları |
| L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 7 gündeki aktivite kaynakları |
| L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 15 gündeki aktivite kaynakları |
| L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 30 gündeki aktivite kaynakları |
| L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 90 gündeki aktivite kaynakları |
| L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 120 gündeki aktivite kaynakları |
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  | Activity Status |
| PREPAID_BASE_TYPE | VARCHAR2 | ✓ |  | Prepaid Base Type |
| PREPAID_BASE_ROTATION | VARCHAR2 | ✓ |  | Prepaid Base Rotation |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-07-01T22:24:18.301952+00:00*

- **ACTV_BOOSTERS**: `Pre KD1 5GB 30D BST`, `Pre KD1 5GB 30D BST | Pre KD3 20GB 30D BST`, `Pre KD1 5GB 30D BST | Pre KD3 20GB 30D BST | Pre KD5 50GB 30D BST`, `Pre KD1 5GB 30D BST | Pre KD5 50GB 30D BST`, `Pre KD3 20GB 30D BST`, `Pre KD3 20GB 30D BST | Pre KD5 50GB 30D BST`, `Pre KD5 50GB 30D BST`, `Pre KD5 50GB 30D BST | go Internet Booster 5KD`, `go Internet Booster 3KD | go Local Booster 1KD`, `go Internet Booster 5KD`
- **ACTV_ENABLERS**: `Camera Access Enabler`, `MBB Enable Calls`
- **ACTV_FREEBIES**: `Anghami prepaid Flag`, `Anghami prepaid Flag | terminated`
- **ACTV_MAINPLAN**: `Prepaid Mobile Package 65 USD`, `go net 12KD 3months`
- **ACTV_VASSERVICES**: `Prepaid Entertainment Menu`, `Prepaid Entertainment Menu | STC TV Prepaid Promo`, `Prepaid Entertainment Menu | stc TV Prepaid Service`, `Prepaid Entertainment Menu | stc tv subscription`, `STC TV Prepaid Promo`, `stc TV Prepaid Service`, `stc tv subscription`
- **BS_FLAG**: `MAIN`
- **BS_TYPE**: `DATA`, `FIBER`, `VOICE`
- **CREDIT_RISK_PROFILE**: `GRAY`, `HIGH`, `LOW`, `MEDIUM`, `NO RISK`, `notfound`
- **ID_TYPE**: ``, `A`, `C`, `D`, `E`, `G`, `P`, `R`, `X`
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: `3PP`, `CHATBOT`, `CMS`, `DCLM`, `DCLMBULK`, `DMPOS`, `ESTORAPP`, `ESTORAPPNEW`, `ESTORWEB`, `ESTORWEBNEW`, `IVR`, `MOBAPP`, `SMS`, `SPPOS`, `TABS`, `WEB`
- **LT_LAST_BUNDLE_PRICE**: `0.34`, `10`, `11`, `12`, `13`, `15`, `16`, `18`, `19`, `20`, `21`, `22`, `3`, `3.5`, `4`, `4.5`, `5`, `6`, `7`, `7.5`, `8`, `9`
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: `AUTO_RENEWAL`, `AUTO_RENEWAL|DEALER`, `AUTO_RENEWAL|DEALER_USSD`, `AUTO_RENEWAL|DEALER_USSD|SMART_PAYMENT`, `AUTO_RENEWAL|DEALER_USSD|USER_USSD`, `AUTO_RENEWAL|SMART_PAYMENT`, `AUTO_RENEWAL|USER`, `AUTO_RENEWAL|USER_USSD`, `DEALER_USSD`, `DEALER_USSD|SMART_PAYMENT`, `DEALER_USSD|SMART_PAYMENT|USER_USSD`, `DEALER|SMART_PAYMENT`, `SMART_PAYMENT`, `SMART_PAYMENT|USER`, `USER`
- **LT_LAST_BUNDLE_TRIGGERMODE**: `0`, `1`, `2`, `3`, `4`, `7`, `8`, `D`, `F`
- **LT_LAST_BUNDLE_VALIDIY**: `28`, `30`, `60`
- **MNP_SUB**: `N`, `Y`
- **NUM_TYPE**: `1`, `2`, `3`, `4`, `5`, `B`, `G`, `H`, `P`, `S`, `V`
- **PREPAID_STATE_GROUP**: `ACTIVE`, `CHURN_WITHIN_MONTH`, `DISABLE`, `GRACE`, `HISTORICAL_CHURN`, `IDLE`, `POOL`, `PREP_TO_POST`
- **PREPOST_PAID**: `POST`, `PREP`
- **REGION**: `AJH`, `AMD`, `ASM`, `FRW`, `HWL`, `KWT`, `MBK`

<!-- ARIA:ENUM-VALUES-END -->
