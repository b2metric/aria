---
table: FCT_PREP_MASTER
database: oracle
workspace: stc-kuwait
keywords: [360 view, account, acquisition, activation, balance, bandwidth, batch,
  billing, bundle, call, channel, contract, country, credit, customer, data, date,
  demographic, etl, financial, geography, income, international, internet, lifecycle,
  master, message, minutes, mobile, money, msisdn, nationality, offer, package, payment,
  phone number, prepaid, product, provision, recharge, revenue, roaming, service,
  sms, snapshot, state, status, subscriber, subscription, tariff, temporal, time,
  topup, touchpoint, travel, usage, voice]
generated_at: 2026-06-07 11:22:23.798133+00:00
enriched_at: '2026-06-07T11:22:24.328660+00:00'
---

# FCT_PREP_MASTER

**Description:** Fact table containing transactional/event data for Prep Master

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | EXEC_DATE | DATE | ✓ |  | Kaydın oluşturulduğu / işin çalıştırıldığı tarih (ETL/batch execution date). | 
 | SNAPSHOT_DATE | DATE | ✓ |  | Verinin hangi güne ait fotoğrafını (snapshot) temsil ettiği tarih. | 
 | CONTRNO | VARCHAR2 | ✓ |  | Sözleşme numarası. Aboneye ait benzersiz sözleşme kimliği. Kullanıcının hayatı boyunca değişmeyen, t | 
 | SUBNO | VARCHAR2 | ✓ |  | MSISDN | 
 | PREPOST_PAID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | APPDATE | DATE | ✓ |  | Hattın aktivasyon / sözleşme başlangıç tarihi (Application Date). | 
| NEXT_APPDATE | DATE | ✓ |  | Next Appdate |
 | ID_NO | VARCHAR2 | ✓ |  | Müşterinin kimlik numarası (residence, pasaport vb.). | 
 | ID_TYPE | VARCHAR2 | ✓ |  | ID_NO da yer alan tanımlayıcının kategorik tipi. | 
 | ICC_NUMBER | VARCHAR2 | ✓ |  | SIM kartın fiziksel seri numarası (Integrated Circuit Card ID). | 
 | IMSI_NUMBER | VARCHAR2 | ✓ |  | Uluslararası mobil abone kimliği (International Mobile Subscriber Identity). Şebekede aboneyi tanıml | 
 | CONTRACT_CATEGORY | VARCHAR2 | ✓ |  | Sözleşme kategorisi (örn. Bireysel, Kurumsal, VIP). | 
| CONTRACT_CATEGORY_GROUP | VARCHAR2 | ✓ |  | Contract Category Group |
| CATEGORY_TYPE | VARCHAR2 | ✓ |  | Category Type |
 | NATIONALITY | VARCHAR2 | ✓ |  | Müşterinin uyruğu (kısa metin). | 
| NATIONALITY_LANG | VARCHAR2 | ✓ |  | Nationality Lang |
 | NATIONALITY_GROUP | VARCHAR2 | ✓ |  | Uyruk ana grubu (örn. Yerel / Yabancı / Körfez ülkeleri). | 
 | NATIONALITY_SUB_GROUP | VARCHAR2 | ✓ |  | Uyruk alt grubu (daha detaylı sınıflandırma). | 
 | BS_TYPE | VARCHAR2 | ✓ |  | Temel hizmet tipi (Basic Service Type) — örn. ses, veri, M2M. | 
| BS_FLAG | VARCHAR2 | ✓ |  | Bs Flag |
| NUM_TYPE | VARCHAR2 | ✓ |  | Num Type |
| RETAILER | VARCHAR2 | ✓ |  | Retailer |
| REGION | VARCHAR2 | ✓ |  | Geographic region |
 | MNP_SUB | VARCHAR2 | ✓ |  | Numara taşıma (Mobile Number Portability) ile gelen abone olup olmadığı bayrağı. | 
 | CREDIT_RISK_PROFILE | VARCHAR2 | ✓ |  | Müşterinin kredi risk profili (düşük/orta/yüksek risk). | 
 | PREPAID_STATE_GROUP | VARCHAR2 | ✓ |  | Ön ödemeli hattın yaşam döngüsü durumu grubu (Aktif, Disable, Grace). | 
 | MAIN_PLAN_PROD_OFFERING_ID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | MAIN_PLAN_NAME | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | MAIN_PLAN_EQUIPID | VARCHAR2 | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | MAIN_PLAN_RENTAL | NUMBER | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | MAIN_PLAN_START_DATE | DATE | ✓ |  | Önemsiz, kullanılmaması gerekir. | 
 | PREP_BAL_AT_MONTH_START | VARCHAR2 | ✓ |  | İçinde bulunulan ayın başındaki ön ödemeli (prepaid) bakiye tutarı | 
 | PREP_BAL_AT_PREV_MONTH_START | VARCHAR2 | ✓ |  | Bugün itibarıyla güncel ön ödemeli bakiye tutarı | 
 | PREP_BAL_AS_OF_TODAY | VARCHAR2 | ✓ |  | Bugün itibarıyla güncel ön ödemeli bakiye tutarı | 
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
 | LT_LAST_BUNDLE_PRICE | NUMBER | ✓ |  | Son alınan paketin fiyatı | 
 | LT_LAST_BUNDLE_ACTV_CHANNEL | VARCHAR2 | ✓ |  | Son paketin aktive edildiği kanal (USSD, IVR, web, uygulama, bayi vb.) | 
 | LT_LAST_BUNDLE_TRIGGERMODE | VARCHAR2 | ✓ |  | Paketin tetiklenme şekli (manuel, otomatik yenileme, kampanya vb.) | 
| LT_LAST_BUNDLE_TRANSACTION_TYP | VARCHAR2 | ✓ |  | Lt Last Bundle Transaction Typ |
 | LT_LAST_BUNDLE_PROV_DATE | DATE | ✓ |  | Paketin sisteme tanımlanma (provisioning) tarihi | 
 | LT_LAST_BUNDLE_CYCLEENDTIME | DATE | ✓ |  | Paket döngüsünün bitiş zamanı | 
 | LT_LAST_BUNDLE_ELAPSECYCLES | NUMBER | ✓ |  | Paketin kaç döngü/periyot kullanıldığı | 
 | LT_LAST_BUNDLE_TERMINATION_DT | DATE | ✓ |  | Paketin sonlandırılma tarihi | 
| LT_LAST_BUNDLE_DATA_GPRS_LOCAL | VARCHAR2 | ✓ |  | Lt Last Bundle Data Gprs Local |
 | LT_LAST_BUNDLE_DATA_ROAMING_MB | NUMBER | ✓ |  | Paketin yurt dışı (roaming) veri kotası (MB) | 
 | LT_LAST_BUNDLE_FREE_DATA_MB | NUMBER | ✓ |  | Paket kapsamındaki ücretsiz/bedava veri miktarı (MB) | 
| LT_LAST_BUNDLE_VOICE_LOCAL_ONN | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Local Onn |
| LT_LAST_BUNDLE_VOICE_LOCAL_OFF | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Local Off |
| LT_LAST_BUNDLE_VOICE_ALL_NET_M | VARCHAR2 | ✓ |  | Lt Last Bundle Voice All Net M |
| LT_LAST_BUNDLE_VOICE_INTERNATI | VARCHAR2 | ✓ |  | Lt Last Bundle Voice Internati |
| LT_LAST_BUNDLE_FREE_ONNET_DURA | VARCHAR2 | ✓ |  | Lt Last Bundle Free Onnet Dura |
| LT_LAST_BUNDLE_FREE_OFFNET_DUR | VARCHAR2 | ✓ |  | Lt Last Bundle Free Offnet Dur |
| LT_LAST_BUNDLE_FREE_INTERCALL_ | VARCHAR2 | ✓ |  | Lt Last Bundle Free Intercall  |
| LT_LAST_BUNDLE_ROAMING_VOICE_M | VARCHAR2 | ✓ |  | Lt Last Bundle Roaming Voice M |
 | LT_LAST_BUNDLE_SMS_LOCAL_CNT | NUMBER | ✓ |  | Yurt içi SMS adedi | 
 | LT_LAST_BUNDLE_SMS_ALL_NET_CNT | NUMBER | ✓ |  | Tüm şebekelere toplam SMS adedi | 
 | LT_LAST_BUNDLE_SMS_INTL_CNT | NUMBER | ✓ |  | Uluslararası SMS adedi | 
 | LT_LAST_BUNDLE_ROAMING_SMS_CNT | NUMBER | ✓ |  | Yurt dışı dolaşımda SMS adedi | 
 | ACTV_ADDONS | VARCHAR2 | ✓ |  | Aktif ek paket (add-on) servisleri | 
 | ACTV_OFFERS | VARCHAR2 | ✓ |  | Aktif kampanya/teklifler | 
 | ACTV_FREEBIES | VARCHAR2 | ✓ |  | Aktif ücretsiz/hediye servisler | 
 | ACTV_DISCOUNTOFFERS | VARCHAR2 | ✓ |  | Aktif indirim teklifleri | 
 | ACTV_VASSERVICES | VARCHAR2 | ✓ |  | Aktif katma değerli servisler (VAS — Value Added Services; örn. ringback tone, içerik servisleri) | 
 | ACTV_ROAMINGBUNDLES | VARCHAR2 | ✓ |  | Aktif yurt dışı dolaşım paketleri | 
 | ACTV_BUNDLES | VARCHAR2 | ✓ |  | Aktif ana paketler | 
 | ACTV_ROAMINGPAYGO | VARCHAR2 | ✓ |  | Aktif kullanım bazlı (pay-as-you-go) roaming servisi | 
 | ACTV_ROAMING_ACCESS | VARCHAR2 | ✓ |  | Yurt dışı dolaşım erişiminin açık/kapalı durumu | 
 | ACTV_ROAMINGLANDINGPAGE | VARCHAR2 | ✓ |  | Roaming landing page (yurt dışına geçince açılan bilgilendirme sayfası) servis durumu | 
 | L1D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 1 günde gelir üreten aktiviteye sahip mi? | 
 | L7D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 7 günde gelir üreten aktiviteye sahip mi? | 
 | L15D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 15 günde gelir üreten aktiviteye sahip mi? | 
 | L30D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 30 günde gelir üreten aktiviteye sahip mi? | 
 | L90D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 90 günde gelir üreten aktiviteye sahip mi? | 
 | L120D_IS_REVENUE_ACTIVE_BASE | NUMBER | ✓ |  | Son 120 günde gelir üreten aktiviteye sahip mi? | 
 | L1D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 1 günde aktif baz içinde mi? | 
 | L7D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 7 günde aktif baz içinde mi? | 
 | L15D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 15 günde aktif baz içinde mi? | 
 | L30D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 30 günde aktif baz içinde mi? | 
 | L90D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 90 günde aktif baz içinde mi? | 
 | L120D_IS_ACTIVE_BASE | VARCHAR2 | ✓ |  | Son 120 günde aktif baz içinde mi? | 
 | L1D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 1 gündeki aktivite kaynakları | 
 | L7D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 7 gündeki aktivite kaynakları | 
 | L15D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 15 gündeki aktivite kaynakları | 
 | L30D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 30 gündeki aktivite kaynakları | 
 | L90D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 90 gündeki aktivite kaynakları | 
 | L120D_ACTIVITY_SOURCES | VARCHAR2 | ✓ |  | Son 120 gündeki aktivite kaynakları | 
| ACTIVITY_STATUS | VARCHAR2 | ✓ |  | Activity Status |

## Keywords

360 view, account, acquisition, activation, balance, bandwidth, batch, billing, bundle, call, channel, contract, country, credit, customer, data, date, demographic, etl, financial, geography, income, international, internet, lifecycle, master, message, minutes, mobile, money, msisdn, nationality, offer, package, payment, phone number, prepaid, product, provision, recharge, revenue, roaming, service, sms, snapshot, state, status, subscriber, subscription, tariff, temporal, time, topup, touchpoint, travel, usage, voice
## Business Metadata


### Column Descriptions

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
