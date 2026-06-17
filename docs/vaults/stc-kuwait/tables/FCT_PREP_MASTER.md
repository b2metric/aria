---
table: FCT_PREP_MASTER
database: oracle
workspace: stc-kuwait
keywords: [bakiye, balance, fact, kpi, master, prepaid, snapshot, summary, özet]
generated_at: '2026-06-16T03:23:43.168994+00:00'
enriched_at: '2026-06-16T14:59:52.296084+00:00'
description: Main fact table that keeps basic metrics, balance, usage and general
  transaction summaries of Prepaid subscribers on a daily basis.
---

# FCT_PREP_MASTER

**Description:** No description provided yet.

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
 | EXEC_DATE | DATE | ✓ |  | The date the record was created / the job was run (ETL/batch execution date). | 
 | SNAPSHOT_DATE | DATE | ✓ |  | The date on which the data represents the snapshot of the day. | 
 | CONTRNO | VARCHAR2 | ✓ |  | Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later. | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | APPDATE | DATE | ✓ |  | Line's activation / contract start date (Application Date). | 
| NEXT_APPDATE | DATE | ✓ |  |  |
 | ID_NO | VARCHAR2 | ✓ |  | Customer's identification number (residence, passport, etc.). | 
 | ID_TYPE | VARCHAR2 | ✓ |  | The categorical type of the identifier contained in ID_NO. | 
 | ICC_NUMBER | VARCHAR2 | ✓ |  | Physical serial number of the SIM card (Integrated Circuit Card ID). | 
 | IMSI_NUMBER | VARCHAR2 | ✓ |  | International Mobile Subscriber Identity. The number that identifies the subscriber in the network. | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Contract category (e.g. Individual, Corporate, VIP). | 
| CONTRACT_CATEGORY_GROUP | VARCHAR2 | ✓ |  |  |
| CATEGORY_TYPE | VARCHAR2 | ✓ |  |  |
 | NATIONALITY | VARCHAR2 | ✓ |  | Nationality of the customer (short text). | 
| NATIONALITY_LANG | VARCHAR2 | ✓ |  |  |
 | NATIONALITY_GROUP | VARCHAR2 | ✓ |  | Nationality major group (e.g. Local / Foreign / Gulf countries). | 
 | NATIONALITY_SUB_GROUP | VARCHAR2 | ✓ |  | Nationality subgroup (more detailed classification). | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Basic service type — e.g. voice, data, M2M. | 
| BS_FLAG | VARCHAR2 | ✓ |  |  |
| NUM_TYPE | VARCHAR2 | ✓ |  |  |
| RETAILER | VARCHAR2 | ✓ |  |  |
| REGION | VARCHAR2 | ✓ |  |  |
 | MNP_SUB | VARCHAR2 | ✓ |  | Flag of whether there is a subscriber coming with number portability (Mobile Number Portability). | 
 | CREDIT_RISK_PROFILE | VARCHAR2 | ✓ |  | Customer's credit risk profile (low/medium/high risk). | 
 | PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Lifecycle status group of the prepaid line (Active, Disable, Grace). | 
 | MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_RENTAL | NUMBER | ✓ |  | It is unimportant and should not be used. | 
 | MAIN_PLAN_START_DATE | DATE | ✓ |  | It is unimportant and should not be used. | 
 | PREP_BAL_AT_MONTH_START | VARCHAR2 | ✓ |  | Prepaid balance amount at the beginning of the current month | 
 | PREP_BAL_AT_PREV_MONTH_START | VARCHAR2 | ✓ |  | Current prepaid balance amount as of today | 
 | PREP_BAL_AS_OF_TODAY | VARCHAR2 | ✓ |  | Current prepaid balance amount as of today | 
 | LT_LAST_ACTIVITY_DT | DATE | ✓ |  | Date of any recent activity on the line | 
 | LT_LAST_DATA_DT | DATE | ✓ |  | Last mobile data (internet) usage date | 
 | LT_LAST_VOICE_OUTGOING_DT | DATE | ✓ |  | Last outgoing voice call date | 
 | LT_LAST_VOICE_INCOMING_DT | DATE | ✓ |  | Last incoming voice call date | 
 | LT_LAST_SMS_OUTGOING_DT | DATE | ✓ |  | Last sent SMS date | 
 | LT_LAST_RECHARGE_DT | DATE | ✓ |  | Last TL top-up (top-up/balance top-up) date | 
 | LT_LAST_ROAMING_DT | DATE | ✓ |  | Last international roaming usage date | 
 | LT_LAST_REVENUE_DT | DATE | ✓ |  | Date of the last transaction that generated income for STC | 
 | LT_LAST_SGWCDR_ACTIVITY_DT | DATE | ✓ |  | Last data activity date according to SGW (Serving Gateway) CDR records (data session based) | 
 | LT_LAST_PAID_SUBSCRIPTION_DT | DATE | ✓ |  | Last paid subscription/package purchase date | 
 | LT_LAST_BUNDLE_PR_ID | VARCHAR2 | ✓ |  | Product ID of the last package received | 
 | LT_LAST_BUNDLE_OFFER_ID | VARCHAR2 | ✓ |  | Offer ID of the last package purchased | 
 | LT_LAST_BUNDLE_OFFER_NAME | VARCHAR2 | ✓ |  | Name of the last package received | 
 | LT_LAST_BUNDLE_VALIDIY | VARCHAR2 | ✓ |  | Validity period of the last package purchased | 
 | LT_LAST_BUNDLE_PRICE | NUMBER | ✓ |  | Price of the last package purchased | 
 | LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.) | 
 | LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | How the package is triggered (manual, automatic renewal, campaign, etc.) | 
| LT_LAST_BUNDLE_TRANSACTION_TYP | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Provisioning date of the package to the system | 
 | LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Packet cycle end time | 
 | LT_LAST_BUNDLE_ELAPSECYCLES | NUMBER | ✓ |  | How many cycles/periods the package has been used | 
 | LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Package termination date | 
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | International (roaming) data quota (MB) of the package | 
 | LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Amount of free data included in the package (MB) | 
| LT_LAST_BUNDLE_VOICE_LOCAL_ONN | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFF | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_ALL_NET_M | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_VOICE_INTERNATI | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_ONNET_DURA | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_OFFNET_DUR | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_FREE_INTERCALL_ | VARCHAR2 | ✓ |  |  |
| LT_LAST_BUNDLE_ROAMING_VOICE_M | VARCHAR2 | ✓ |  |  |
 | LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Number of domestic SMS | 
 | LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Total number of SMS to all networks | 
 | LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Number of international SMS | 
 | LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Number of SMS in international roaming | 
 | ACTV_ADDONS | VARCHAR2 | ✓ |  | Active additional package (add-on) services | 
 | ACTV_OFFERS | VARCHAR2 | ✓ |  | Active campaigns/offers | 
 | ACTV_FREEBIES | VARCHAR2 | ✓ |  | Active free/gift services | 
 | ACTV_DISCOUNTOFFERS | VARCHAR2 | ✓ |  | Active discount offers | 
 | ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Active value added services (VAS — Value Added Services; e.g. ringback tone, content services) | 
 | ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Active international roaming packages | 
 | ACTV_BUNDLES | VARCHAR2 | ✓ |  | Active main packages | 
 | ACTV_ROAMINGPAYGO | VARCHAR2 | ✓ |  | Active usage based (pay-as-you-go) roaming service | 
 | ACTV_ROAMING_ACCESS | VARCHAR2 | ✓ |  | On/off status of international roaming access | 
 | ACTV_ROAMINGLANDINGPAGE | VARCHAR2 | ✓ |  | Roaming landing page (information page that opens when you go abroad) service status | 
 | L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has there been any income generating activity in the last day? | 
 | L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has he had income-producing activity in the last 7 days? | 
 | L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Has he had income-producing activity in the last 15 days? | 
 | L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have income-producing activity in the last 30 days? | 
 | L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have revenue-producing activity in the last 90 days? | 
 | L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Does it have income-producing activity in the last 120 days? | 
 | L1D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last day? | 
 | L7D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 7 days? | 
 | L15D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 15 days? | 
 | L30D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 30 days? | 
 | L90D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 90 days? | 
 | L120D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Is it in the active base in the last 120 days? | 
 | L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources in the last day | 
 | L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources for the last 7 days | 
 | L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Sources of activity in the last 15 days | 
 | L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 30 days | 
 | L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 90 days | 
 | L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Activity sources from the last 120 days | 
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  |  |

## Keywords

## Column Descriptions
- **EXEC_DATE**: 
- **SNAPSHOT_DATE**: 
- **CONTRNO**: 
- **SUBNO**: 
- **PREPOST_PAID**: 
- **APPDATE**: 
- **NEXT_APPDATE**: 
- **ID_NO**: 
- **ID_TYPE**: 
- **ICC_NUMBER**: 
- **IMSI_NUMBER**: 
- **CONTRACT_CATEGORY**: 
- **CONTRACT_CATEGORY_GROUP**: 
- **CATEGORY_TYPE**: 
- **NATIONALITY**: 
- **NATIONALITY_LANG**: 
- **NATIONALITY_GROUP**: 
- **NATIONALITY_SUB_GROUP**: 
- **BS_TYPE**: 
- **BS_FLAG**: 
- **NUM_TYPE**: 
- **RETAILER**: 
- **REGION**: 
- **MNP_SUB**: 
- **CREDIT_RISK_PROFILE**: 
- **PREPAID_STATE_GROUP**: 
- **MAIN_PLAN_PROD_OFFERING_ID**: 
- **MAIN_PLAN_NAME**: 
- **MAIN_PLAN_EQUIPID**: 
- **MAIN_PLAN_RENTAL**: 
- **MAIN_PLAN_START_DATE**: 
- **PREP_BAL_AT_MONTH_START**: 
- **PREP_BAL_AT_PREV_MONTH_START**: 
- **PREP_BAL_AS_OF_TODAY**: 
- **LT_LAST_ACTIVITY_DT**: 
- **LT_LAST_DATA_DT**: 
- **LT_LAST_VOICE_OUTGOING_DT**: 
- **LT_LAST_VOICE_INCOMING_DT**: 
- **LT_LAST_SMS_OUTGOING_DT**: 
- **LT_LAST_RECHARGE_DT**: 
- **LT_LAST_ROAMING_DT**: 
- **LT_LAST_REVENUE_DT**: 
- **LT_LAST_SGWCDR_ACTIVITY_DT**: 
- **LT_LAST_PAID_SUBSCRIPTION_DT**: 
- **LT_LAST_BUNDLE_PR_ID**: 
- **LT_LAST_BUNDLE_OFFER_ID**: 
- **LT_LAST_BUNDLE_OFFER_NAME**: 
- **LT_LAST_BUNDLE_VALIDIY**: 
- **LT_LAST_BUNDLE_PRICE**: 
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: 
- **LT_LAST_BUNDLE_TRIGGERMODE**: 
- **LT_LAST_BUNDLE_TRANSACTION_TYP**: 
- **LT_LAST_BUNDLE_PROV_DATE**: 
- **LT_LAST_BUNDLE_CYCLEENDTIME**: 
- **LT_LAST_BUNDLE_ELAPSECYCLES**: 
- **LT_LAST_BUNDLE_TERMINATION_DT**: 
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL**: 
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: 
- **LT_LAST_BUNDLE_FREE_DATA_MB**: 
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONN**: 
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFF**: 
- **LT_LAST_BUNDLE_VOICE_ALL_NET_M**: 
- **LT_LAST_BUNDLE_VOICE_INTERNATI**: 
- **LT_LAST_BUNDLE_FREE_ONNET_DURA**: 
- **LT_LAST_BUNDLE_FREE_OFFNET_DUR**: 
- **LT_LAST_BUNDLE_FREE_INTERCALL_**: 
- **LT_LAST_BUNDLE_ROAMING_VOICE_M**: 
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: 
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: 
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: 
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: 
- **ACTV_ADDONS**: 
- **ACTV_OFFERS**: 
- **ACTV_FREEBIES**: 
- **ACTV_DISCOUNTOFFERS**: 
- **ACTV_VASSERVICES**: 
- **ACTV_ROAMINGBUNDLES**: 
- **ACTV_BUNDLES**: 
- **ACTV_ROAMINGPAYGO**: 
- **ACTV_ROAMING_ACCESS**: 
- **ACTV_ROAMINGLANDINGPAGE**: 
- **L1D_IS_REVENUE_ACTIVE_BASE**: 
- **L7D_IS_REVENUE_ACTIVE_BASE**: 
- **L15D_IS_REVENUE_ACTIVE_BASE**: 
- **L30D_IS_REVENUE_ACTIVE_BASE**: 
- **L90D_IS_REVENUE_ACTIVE_BASE**: 
- **L120D_IS_REVENUE_ACTIVE_BASE**: 
- **L1D_IS_ACTIVE_BASE**: 
- **L7D_IS_ACTIVE_BASE**: 
- **L15D_IS_ACTIVE_BASE**: 
- **L30D_IS_ACTIVE_BASE**: 
- **L90D_IS_ACTIVE_BASE**: 
- **L120D_IS_ACTIVE_BASE**: 
- **L1D_ACTIVITY_SOURCES**: 
- **L7D_ACTIVITY_SOURCES**: 
- **L15D_ACTIVITY_SOURCES**: 
- **L30D_ACTIVITY_SOURCES**: 
- **L90D_ACTIVITY_SOURCES**: 
- **L120D_ACTIVITY_SOURCES**: 
- **ACTIVITY_STATUS**:
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **SNAPSHOT_DATE**: Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih.
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **ID_NO**: Müşterinin kimlik numarası (residence, pasaport vb.).
- **ID_TYPE**: ID_NO da yer alan tanımlayıcının kategorik tipi.
- **ICC_NUMBER**: SIM kartın fiziksel seri numarası (Integrated Circuit Card ID).
- **IMSI_NUMBER**: Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **NATIONALITY_GROUP**: Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri).
- **NATIONALITY_SUB_GROUP**: Uyruk alt grubu (daha detaylı sınıflandırma).
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **MNP_SUB**: Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı.
- **CREDIT_RISK_PROFILE**: Müşterinin kredi risk profili (düşük/orta/yüksek risk).
- **PREPAID_STATE_GROUP**: Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_NAME**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_EQUIPID**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_RENTAL**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_START_DATE**: Önemsiz, kullanılmaması gerekir.
- **PREP_BAL_AT_MONTH_START**: İçinde bulunulan ayın başındaki ön ödemeli (prepaid) bakiye tutarı
- **PREP_BAL_AT_PREV_MONTH_START**: Bugün itibarıyla güncel ön ödemeli bakiye tutarı
- **PREP_BAL_AS_OF_TODAY**: Bugün itibarıyla güncel ön ödemeli bakiye tutarı
- **LT_LAST_ACTIVITY_DT**: Hat üzerinde gerçekleşen son herhangi bir aktivitenin tarihi
- **LT_LAST_DATA_DT**: Son mobil veri (internet) kullanım tarihi
- **LT_LAST_VOICE_OUTGOING_DT**: Son giden sesli arama tarihi
- **LT_LAST_VOICE_INCOMING_DT**: Son gelen sesli arama tarihi
- **LT_LAST_SMS_OUTGOING_DT**: Son giden SMS tarihi
- **LT_LAST_RECHARGE_DT**: Son TL yükleme (kontör/bakiye yükleme) tarihi
- **LT_LAST_ROAMING_DT**: Son uluslararası dolaşım (roaming) kullanım tarihi
- **LT_LAST_REVENUE_DT**: STC'e gelir yaratan son işlemin tarihi
- **LT_LAST_SGWCDR_ACTIVITY_DT**: SGW (Serving Gateway) CDR kayıtlarına göre son veri aktivite tarihi (data oturumu bazlı)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Son ücretli abonelik/paket satın alma tarihi
- **LT_LAST_BUNDLE_PR_ID**: Son alınan paketin ürün (product) ID'si
- **LT_LAST_BUNDLE_OFFER_ID**: Son alınan paketin teklif (offer) ID'si
- **LT_LAST_BUNDLE_OFFER_NAME**: Son alınan paketin adı
- **LT_LAST_BUNDLE_VALIDIY**: Son alınan paketin geçerlilik süresi
- **LT_LAST_BUNDLE_PRICE**: Son alınan paketin fiyatı
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Son paketin aktive edildiği kanal (USSD, IVR, web, uygulama, bayi vb.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: Paketin tetiklenme şekli (manuel, otomatik yenileme, kampanya vb.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Paket işlem tipi (ilk alım, yenileme, upgrade vb.)
- **LT_LAST_BUNDLE_PROV_DATE**: Paketin sisteme tanımlanma (provisioning) tarihi
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Paket döngüsünün bitiş zamanı
- **LT_LAST_BUNDLE_ELAPSECYCLES**: Paketin kaç döngü/periyot kullanıldığı
- **LT_LAST_BUNDLE_TERMINATION_DT**: Paketin sonlandırılma tarihi
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Paketin yurt içi mobil veri kotası (MB)
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: Paketin yurt dışı (roaming) veri kotası (MB)
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Paket kapsamındaki ücretsiz/bedava veri miktarı (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Yurt içi şebeke içi (aynı operatör) konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Yurt içi şebeke dışı (diğer operatörler) konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Tüm yurt içi şebekelere (on-net + off-net) toplam konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: Uluslararası arama (yurt dışını arama) dakikası
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Şebeke içi ücretsiz konuşma dakikası
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Şebeke dışı ücretsiz konuşma dakikası
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Şebekeler arası ücretsiz konuşma dakikası (intercall — operatörler arası)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Yurt dışı dolaşımda konuşma dakikası
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Yurt içi SMS adedi
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Tüm şebekelere toplam SMS adedi
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Uluslararası SMS adedi
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Yurt dışı dolaşımda SMS adedi
- **ACTV_ADDONS**: Aktif ek paket (add-on) servisleri
- **ACTV_OFFERS**: Aktif kampanya/teklifler
- **ACTV_FREEBIES**: Aktif ücretsiz/hediye servisler
- **ACTV_DISCOUNTOFFERS**: Aktif indirim teklifleri
- **ACTV_VASSERVICES**: Aktif katma değerli servisler (VAS — Value Added Services; örn. ringback tone, içerik servisleri)
- **ACTV_ROAMINGBUNDLES**: Aktif yurt dışı dolaşım paketleri
- **ACTV_BUNDLES**: Aktif ana paketler
- **ACTV_ROAMINGPAYGO**: Aktif kullanım bazlı (pay-as-you-go) roaming servisi
- **ACTV_ROAMING_ACCESS**: Yurt dışı dolaşım erişiminin açık/kapalı durumu
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (yurt dışına geçince açılan bilgilendirme sayfası) servis durumu
- **L1D_IS_REVENUE_ACTIVE_BASE**: Son 1 günde gelir üreten aktiviteye sahip mi?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Son 7 günde gelir üreten aktiviteye sahip mi?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Son 15 günde gelir üreten aktiviteye sahip mi?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Son 30 günde gelir üreten aktiviteye sahip mi?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Son 90 günde gelir üreten aktiviteye sahip mi?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Son 120 günde gelir üreten aktiviteye sahip mi?
- **L1D_IS_ACTIVE_BASE**: Son 1 günde aktif baz içinde mi?
- **L7D_IS_ACTIVE_BASE**: Son 7 günde aktif baz içinde mi?
- **L15D_IS_ACTIVE_BASE**: Son 15 günde aktif baz içinde mi?
- **L30D_IS_ACTIVE_BASE**: Son 30 günde aktif baz içinde mi?
- **L90D_IS_ACTIVE_BASE**: Son 90 günde aktif baz içinde mi?
- **L120D_IS_ACTIVE_BASE**: Son 120 günde aktif baz içinde mi?
- **L1D_ACTIVITY_SOURCES**: Son 1 gündeki aktivite kaynakları
- **L7D_ACTIVITY_SOURCES**: Son 7 gündeki aktivite kaynakları
- **L15D_ACTIVITY_SOURCES**: Son 15 gündeki aktivite kaynakları
- **L30D_ACTIVITY_SOURCES**: Son 30 gündeki aktivite kaynakları
- **L90D_ACTIVITY_SOURCES**: Son 90 gündeki aktivite kaynakları
- **L120D_ACTIVITY_SOURCES**: Son 120 gündeki aktivite kaynakları
## Column Descriptions

- **EXEC_DATE**: Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date).
- **SNAPSHOT_DATE**: Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih.
- **CONTRNO**: Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, tekil tanımlayıcı, kullanıcı seneler sonra tekrar bir numara aktifleştirse dahi aynı kimliği tekrar alır.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: Önemsiz, kullanılmaması gerekir.
- **APPDATE**: Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date).
- **ID_NO**: Müşterinin kimlik numarası (residence, pasaport vb.).
- **ID_TYPE**: ID_NO da yer alan tanımlayıcının kategorik tipi.
- **ICC_NUMBER**: SIM kartın fiziksel seri numarası (Integrated Circuit Card ID).
- **IMSI_NUMBER**: Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanımlayan numara.
- **CONTRACT_CATEGORY**: Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP).
- **NATIONALITY**: Müşterinin uyruğu (kısa metin).
- **NATIONALITY_GROUP**: Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri).
- **NATIONALITY_SUB_GROUP**: Uyruk alt grubu (daha detaylı sınıflandırma).
- **BS_TYPE**: Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M.
- **MNP_SUB**: Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı.
- **CREDIT_RISK_PROFILE**: Müşterinin kredi risk profili (düşük/orta/yüksek risk).
- **PREPAID_STATE_GROUP**: Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_NAME**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_EQUIPID**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_RENTAL**: Önemsiz, kullanılmaması gerekir.
- **MAIN_PLAN_START_DATE**: Önemsiz, kullanılmaması gerekir.
- **PREP_BAL_AT_MONTH_START**: İçinde bulunulan ayın başındaki ön ödemeli (prepaid) bakiye tutarı
- **PREP_BAL_AT_PREV_MONTH_START**: Bugün itibarıyla güncel ön ödemeli bakiye tutarı
- **PREP_BAL_AS_OF_TODAY**: Bugün itibarıyla güncel ön ödemeli bakiye tutarı
- **LT_LAST_ACTIVITY_DT**: Hat üzerinde gerçekleşen son herhangi bir aktivitenin tarihi
- **LT_LAST_DATA_DT**: Son mobil veri (internet) kullanım tarihi
- **LT_LAST_VOICE_OUTGOING_DT**: Son giden sesli arama tarihi
- **LT_LAST_VOICE_INCOMING_DT**: Son gelen sesli arama tarihi
- **LT_LAST_SMS_OUTGOING_DT**: Son giden SMS tarihi
- **LT_LAST_RECHARGE_DT**: Son TL yükleme (kontör/bakiye yükleme) tarihi
- **LT_LAST_ROAMING_DT**: Son uluslararası dolaşım (roaming) kullanım tarihi
- **LT_LAST_REVENUE_DT**: STC'e gelir yaratan son işlemin tarihi
- **LT_LAST_SGWCDR_ACTIVITY_DT**: SGW (Serving Gateway) CDR kayıtlarına göre son veri aktivite tarihi (data oturumu bazlı)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Son ücretli abonelik/paket satın alma tarihi
- **LT_LAST_BUNDLE_PR_ID**: Son alınan paketin ürün (product) ID'si
- **LT_LAST_BUNDLE_OFFER_ID**: Son alınan paketin teklif (offer) ID'si
- **LT_LAST_BUNDLE_OFFER_NAME**: Son alınan paketin adı
- **LT_LAST_BUNDLE_VALIDIY**: Son alınan paketin geçerlilik süresi
- **LT_LAST_BUNDLE_PRICE**: Son alınan paketin fiyatı
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Son paketin aktive edildiği kanal (USSD, IVR, web, uygulama, bayi vb.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: Paketin tetiklenme şekli (manuel, otomatik yenileme, kampanya vb.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Paket işlem tipi (ilk alım, yenileme, upgrade vb.)
- **LT_LAST_BUNDLE_PROV_DATE**: Paketin sisteme tanımlanma (provisioning) tarihi
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Paket döngüsünün bitiş zamanı
- **LT_LAST_BUNDLE_ELAPSECYCLES**: Paketin kaç döngü/periyot kullanıldığı
- **LT_LAST_BUNDLE_TERMINATION_DT**: Paketin sonlandırılma tarihi
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Paketin yurt içi mobil veri kotası (MB)
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: Paketin yurt dışı (roaming) veri kotası (MB)
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Paket kapsamındaki ücretsiz/bedava veri miktarı (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Yurt içi şebeke içi (aynı operatör) konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Yurt içi şebeke dışı (diğer operatörler) konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Tüm yurt içi şebekelere (on-net + off-net) toplam konuşma dakikası
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: Uluslararası arama (yurt dışını arama) dakikası
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Şebeke içi ücretsiz konuşma dakikası
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Şebeke dışı ücretsiz konuşma dakikası
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Şebekeler arası ücretsiz konuşma dakikası (intercall — operatörler arası)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Yurt dışı dolaşımda konuşma dakikası
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Yurt içi SMS adedi
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Tüm şebekelere toplam SMS adedi
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Uluslararası SMS adedi
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Yurt dışı dolaşımda SMS adedi
- **ACTV_ADDONS**: Aktif ek paket (add-on) servisleri
- **ACTV_OFFERS**: Aktif kampanya/teklifler
- **ACTV_FREEBIES**: Aktif ücretsiz/hediye servisler
- **ACTV_DISCOUNTOFFERS**: Aktif indirim teklifleri
- **ACTV_VASSERVICES**: Aktif katma değerli servisler (VAS — Value Added Services; örn. ringback tone, içerik servisleri)
- **ACTV_ROAMINGBUNDLES**: Aktif yurt dışı dolaşım paketleri
- **ACTV_BUNDLES**: Aktif ana paketler
- **ACTV_ROAMINGPAYGO**: Aktif kullanım bazlı (pay-as-you-go) roaming servisi
- **ACTV_ROAMING_ACCESS**: Yurt dışı dolaşım erişiminin açık/kapalı durumu
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (yurt dışına geçince açılan bilgilendirme sayfası) servis durumu
- **L1D_IS_REVENUE_ACTIVE_BASE**: Son 1 günde gelir üreten aktiviteye sahip mi?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Son 7 günde gelir üreten aktiviteye sahip mi?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Son 15 günde gelir üreten aktiviteye sahip mi?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Son 30 günde gelir üreten aktiviteye sahip mi?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Son 90 günde gelir üreten aktiviteye sahip mi?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Son 120 günde gelir üreten aktiviteye sahip mi?
- **L1D_IS_ACTIVE_BASE**: Son 1 günde aktif baz içinde mi?
- **L7D_IS_ACTIVE_BASE**: Son 7 günde aktif baz içinde mi?
- **L15D_IS_ACTIVE_BASE**: Son 15 günde aktif baz içinde mi?
- **L30D_IS_ACTIVE_BASE**: Son 30 günde aktif baz içinde mi?
- **L90D_IS_ACTIVE_BASE**: Son 90 günde aktif baz içinde mi?
- **L120D_IS_ACTIVE_BASE**: Son 120 günde aktif baz içinde mi?
- **L1D_ACTIVITY_SOURCES**: Son 1 gündeki aktivite kaynakları
- **L7D_ACTIVITY_SOURCES**: Son 7 gündeki aktivite kaynakları
- **L15D_ACTIVITY_SOURCES**: Son 15 gündeki aktivite kaynakları
- **L30D_ACTIVITY_SOURCES**: Son 30 gündeki aktivite kaynakları
- **L90D_ACTIVITY_SOURCES**: Son 90 gündeki aktivite kaynakları
- **L120D_ACTIVITY_SOURCES**: Son 120 gündeki aktivite kaynakları
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
## Business Metadata

**Description:** Main fact table that keeps basic metrics, balance, usage and general transaction summaries of Prepaid subscribers on a daily basis.

### Column Descriptions

- **EXEC_DATE**: The date the record was created / the job was run (ETL/batch execution date).
- **SNAPSHOT_DATE**: The date on which the data represents the snapshot of the day.
- **CONTRNO**: Contract number. Unique contract ID of the subscriber. The unique identifier, which does not change throughout the user's life, receives the same ID again even if the user reactivates a number years later.
- **SUBNO**: MSISDN
- **PREPOST_PAID**: It is unimportant and should not be used.
- **APPDATE**: Line's activation / contract start date (Application Date).
- **ID_NO**: Customer's identification number (residence, passport, etc.).
- **ID_TYPE**: The categorical type of the identifier contained in ID_NO.
- **ICC_NUMBER**: Physical serial number of the SIM card (Integrated Circuit Card ID).
- **IMSI_NUMBER**: International Mobile Subscriber Identity. The number that identifies the subscriber in the network.
- **CONTRACT_CATEGORY**: Contract category (e.g. Individual, Corporate, VIP).
- **NATIONALITY**: Nationality of the customer (short text).
- **NATIONALITY_GROUP**: Nationality major group (e.g. Local / Foreign / Gulf countries).
- **NATIONALITY_SUB_GROUP**: Nationality subgroup (more detailed classification).
- **BS_TYPE**: Basic service type — e.g. voice, data, M2M.
- **MNP_SUB**: Flag of whether there is a subscriber coming with number portability (Mobile Number Portability).
- **CREDIT_RISK_PROFILE**: Customer's credit risk profile (low/medium/high risk).
- **PREPAID_STATE_GROUP**: Lifecycle status group of the prepaid line (Active, Disable, Grace).
- **MAIN_PLAN_PROD_OFFERING_ID**: It is unimportant and should not be used.
- **MAIN_PLAN_NAME**: It is unimportant and should not be used.
- **MAIN_PLAN_EQUIPID**: It is unimportant and should not be used.
- **MAIN_PLAN_RENTAL**: It is unimportant and should not be used.
- **MAIN_PLAN_START_DATE**: It is unimportant and should not be used.
- **PREP_BAL_AT_MONTH_START**: Prepaid balance amount at the beginning of the current month
- **PREP_BAL_AT_PREV_MONTH_START**: Current prepaid balance amount as of today
- **PREP_BAL_AS_OF_TODAY**: Current prepaid balance amount as of today
- **LT_LAST_ACTIVITY_DT**: Date of any recent activity on the line
- **LT_LAST_DATA_DT**: Last mobile data (internet) usage date
- **LT_LAST_VOICE_OUTGOING_DT**: Last outgoing voice call date
- **LT_LAST_VOICE_INCOMING_DT**: Last incoming voice call date
- **LT_LAST_SMS_OUTGOING_DT**: Last sent SMS date
- **LT_LAST_RECHARGE_DT**: Last TL top-up (top-up/balance top-up) date
- **LT_LAST_ROAMING_DT**: Last international roaming usage date
- **LT_LAST_REVENUE_DT**: Date of the last transaction that generated income for STC
- **LT_LAST_SGWCDR_ACTIVITY_DT**: Last data activity date according to SGW (Serving Gateway) CDR records (data session based)
- **LT_LAST_PAID_SUBSCRIPTION_DT**: Last paid subscription/package purchase date
- **LT_LAST_BUNDLE_PR_ID**: Product ID of the last package received
- **LT_LAST_BUNDLE_OFFER_ID**: Offer ID of the last package purchased
- **LT_LAST_BUNDLE_OFFER_NAME**: Name of the last package received
- **LT_LAST_BUNDLE_VALIDIY**: Validity period of the last package purchased
- **LT_LAST_BUNDLE_PRICE**: Price of the last package purchased
- **LT_LAST_BUNDLE_ACTV_CHANNEL**: Channel where the last package was activated (USSD, IVR, web, app, reseller, etc.)
- **LT_LAST_BUNDLE_TRIGGERMODE**: How the package is triggered (manual, automatic renewal, campaign, etc.)
- **LT_LAST_BUNDLE_TRANSACTION_TYPE**: Package transaction type (first purchase, renewal, upgrade, etc.)
- **LT_LAST_BUNDLE_PROV_DATE**: Provisioning date of the package to the system
- **LT_LAST_BUNDLE_CYCLEENDTIME**: Packet cycle end time
- **LT_LAST_BUNDLE_ELAPSECYCLES**: How many cycles/periods the package has been used
- **LT_LAST_BUNDLE_TERMINATION_DT**: Package termination date
- **LT_LAST_BUNDLE_DATA_GPRS_LOCAL_MB**: Domestic mobile data quota (MB) of the package
- **LT_LAST_BUNDLE_DATA_ROAMING_MB**: International (roaming) data quota (MB) of the package
- **LT_LAST_BUNDLE_FREE_DATA_MB**: Amount of free data included in the package (MB)
- **LT_LAST_BUNDLE_VOICE_LOCAL_ONNET_MIN**: Domestic on-net (same operator) call minutes
- **LT_LAST_BUNDLE_VOICE_LOCAL_OFFNET_MIN**: Domestic off-net (other operators) call minutes
- **LT_LAST_BUNDLE_VOICE_ALL_NET_MIN**: Total call minutes to all domestic networks (on-net + off-net)
- **LT_LAST_BUNDLE_VOICE_INTERNATIONAL_MIN**: International calling (calling abroad) minutes
- **LT_LAST_BUNDLE_FREE_ONNET_DURATION_MIN**: Free on-net call minutes
- **LT_LAST_BUNDLE_FREE_OFFNET_DURATION_MIN**: Free off-net call minutes
- **LT_LAST_BUNDLE_FREE_INTERCALL_DURATION_MIN**: Free inter-network call minutes (intercall — inter-operator)
- **LT_LAST_BUNDLE_ROAMING_VOICE_MIN**: Talk minutes when roaming abroad
- **LT_LAST_BUNDLE_SMS_LOCAL_CNT**: Number of domestic SMS
- **LT_LAST_BUNDLE_SMS_ALL_NET_CNT**: Total number of SMS to all networks
- **LT_LAST_BUNDLE_SMS_INTL_CNT**: Number of international SMS
- **LT_LAST_BUNDLE_ROAMING_SMS_CNT**: Number of SMS in international roaming
- **ACTV_ADDONS**: Active additional package (add-on) services
- **ACTV_OFFERS**: Active campaigns/offers
- **ACTV_FREEBIES**: Active free/gift services
- **ACTV_DISCOUNTOFFERS**: Active discount offers
- **ACTV_VASSERVICES**: Active value added services (VAS — Value Added Services; e.g. ringback tone, content services)
- **ACTV_ROAMINGBUNDLES**: Active international roaming packages
- **ACTV_BUNDLES**: Active main packages
- **ACTV_ROAMINGPAYGO**: Active usage based (pay-as-you-go) roaming service
- **ACTV_ROAMING_ACCESS**: On/off status of international roaming access
- **ACTV_ROAMINGLANDINGPAGE**: Roaming landing page (information page that opens when you go abroad) service status
- **L1D_IS_REVENUE_ACTIVE_BASE**: Has there been any income generating activity in the last day?
- **L7D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 7 days?
- **L15D_IS_REVENUE_ACTIVE_BASE**: Has he had income-producing activity in the last 15 days?
- **L30D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 30 days?
- **L90D_IS_REVENUE_ACTIVE_BASE**: Does it have revenue-producing activity in the last 90 days?
- **L120D_IS_REVENUE_ACTIVE_BASE**: Does it have income-producing activity in the last 120 days?
- **L1D_IS_ACTIVE_BASE**: Is it in the active base in the last day?
- **L7D_IS_ACTIVE_BASE**: Is it in the active base in the last 7 days?
- **L15D_IS_ACTIVE_BASE**: Is it in the active base in the last 15 days?
- **L30D_IS_ACTIVE_BASE**: Is it in the active base in the last 30 days?
- **L90D_IS_ACTIVE_BASE**: Is it in the active base in the last 90 days?
- **L120D_IS_ACTIVE_BASE**: Is it in the active base in the last 120 days?
- **L1D_ACTIVITY_SOURCES**: Activity sources in the last day
- **L7D_ACTIVITY_SOURCES**: Activity sources for the last 7 days
- **L15D_ACTIVITY_SOURCES**: Sources of activity in the last 15 days
- **L30D_ACTIVITY_SOURCES**: Activity sources from the last 30 days
- **L90D_ACTIVITY_SOURCES**: Activity sources from the last 90 days
- **L120D_ACTIVITY_SOURCES**: Activity sources from the last 120 days
