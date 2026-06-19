---
table: ALL_RAW
database: oracle
workspace: medianova
keywords: [access log, bandwidth, cdn, country, data, date, demographic, edge, geography,
  internet, istek, lifecycle, log, nationality, raw, request, state, status, temporal,
  time, traffic, usage]
generated_at: 2026-06-19 08:10:39.174474+00:00
description: 'Medianova CDN edge tarafından sunulan her istek için bir satır içeren
  ham HTTP erişim günlüğü. Tüm trafik, gecikme, önbellek ve izleyici analizi için
  temel kaynak. 2026-06-01..2026-06-12 arasını kapsar (7-10 Haziran''da 4 günlük boşluk).
  Uyarı: 16.127 satırda Q_TIMESTAMP = 1970-01-01 (geçersiz); gerçek olay zamanı için
  TIMESTAMP kullanın.'
business_name: Ham CDN Edge İstekleri
data_domain: CDN Dağıtımı
enriched_at: '2026-06-19T09:35:41.377396+00:00'
---

# ALL_RAW

**Description:** Table containing All Raw data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | Q_TIMESTAMP | TIMESTAMP(6) | ✓ |  | Analitik saati; ~16k satır 1970-01-01 (geçersiz) — zaman filtreleme için KULLANMAYIN. | 
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Önbellek sonucu: HIT (edge'den sunuldu ~0.045s), MISS (~0.210s), EXPIRED (~0.286s) veya boş (önbelleklenemez). Önbellek İsabet Oranını belirler. | 
 | TIMESTAMP | TIMESTAMP(6) | ✓ |  | İsteğin gerçek olay zamanı (zaman filtreleri için bunu kullanın). | 
| REMOTE_ADDR | VARCHAR2 | ✓ |  | Remote Addr |
| REMOTE_PORT | VARCHAR2 | ✓ |  | Remote Port |
| REQUEST_ADDR | VARCHAR2 | ✓ |  | Request Addr |
| SERVER_NAME | VARCHAR2 | ✓ |  | Server Name |
| SERVER_PORT | NUMBER | ✓ |  | Server Port |
 | BODY_BYTES_SENT | NUMBER | ✓ |  | Yalnızca yanıt gövde baytları (başlıklar hariç). | 
 | BYTES_SENT | NUMBER | ✓ |  | İstemciye gönderilen toplam bayt (başlıklar + gövde). Birincil bant genişliği/veri aktarımı ölçüsü. | 
| BODY_RECEIVED | NUMBER | ✓ |  | Body Received |
 | REQUEST_TIME | NUMBER | ✓ |  | İsteği sunmak için geçen toplam saniye — temel gecikme metriği. | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP yanıt kodu. 200 OK (~%80), 410 Gone (~%17.5, zararsız — süresi dolmuş canlı yayın segmentleri), 304 Not Modified (~%2). 410'u gerçek 5xx hatalarından ayrı değerlendirin. | 
 | REQUEST_URI | VARCHAR2 | ✓ |  | İstenen URI/yol (DASH .mpd manifestleri, HLS .m3u8 oynatma listeleri, medya segmentleri). | 
| REQUEST_PARAM | VARCHAR2 | ✓ |  | Request Param |
| REQUEST_METHOD | VARCHAR2 | ✓ |  | Request Method |
| UPSTREAM_ADDR | VARCHAR2 | ✓ |  | Upstream Addr |
| UPSTREAM_RESPONSE_TIME | NUMBER | ✓ |  | Upstream Response Time |
| UPSTREAM_CONNECT_TIME | NUMBER | ✓ |  | Upstream Connect Time |
| UPSTREAM_HEADER_TIME | NUMBER | ✓ |  | Upstream Header Time |
| UPSTREAM_STATUS | VARCHAR2 | ✓ |  | Upstream Status |
| SCHEME | VARCHAR2 | ✓ |  | Scheme |
| HTTP_REFERRER | VARCHAR2 | ✓ |  | Http Referrer |
 | TCPINFO_RTT | VARCHAR2 | ✓ |  | TCP gidiş-dönüş süresi (ağ mesafesi sinyali), mikrosaniye. | 
| TCPINFO_RTTVAR | VARCHAR2 | ✓ |  | Tcpinfo Rttvar |
| SSL_PROTOCOL | VARCHAR2 | ✓ |  | Ssl Protocol |
| SSL_CIPHER | VARCHAR2 | ✓ |  | Ssl Cipher |
| REQUEST_ID | VARCHAR2 | ✓ |  | Request Id |
| ROLE | VARCHAR2 | ✓ |  | Role |
| HTTP_RANGE | VARCHAR2 | ✓ |  | Http Range |
 | ACCOUNT_TYPE | VARCHAR2 | ✓ |  | Müşteri hesap katmanı. | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | İsteği sunan CDN önbellek katmanı: Node (edge, ~%62 isabet), Mcache (orta), Feda (sadece getir, tasarım gereği %0 isabet). | 
| HTTP_X_FORWARDED_FOR | VARCHAR2 | ✓ |  | Http X Forwarded For |
| HTTP_PROTOCOL | VARCHAR2 | ✓ |  | Http Protocol |
 | RESOURCE_NAME | VARCHAR2 | ✓ |  | CDN özelliği/kaynağı (örn. b2metric-video.lg, ssport-live). | 
| ORG_NAME | VARCHAR2 | ✓ |  | Org Name |
| RESOURCE_UUID | VARCHAR2 | ✓ |  | Resource Uuid |
 | HTTP_USER_AGENT | VARCHAR2 | ✓ |  | İstemci kullanıcı aracısı — cihaz/tarayıcı/işletim sistemi izleyici ilişkilendirmesi için kaynak. | 
| HOST_ROLE | VARCHAR2 | ✓ |  | Host Role |
| TENANT_CODE | VARCHAR2 | ✓ |  | Tenant Code |
 | DATACENTER | VARCHAR2 | ✓ |  | İsteği sunan uç nokta (PoP), şehir.sağlayıcı olarak adlandırılır (örn. ist.mrs = İstanbul). İstanbul PoP'leri en düşük gecikme (15-26ms); Sidney en yüksek (~275ms). | 
| CDN_ROLE | VARCHAR2 | ✓ |  | Cdn Role |
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | İstemci ülkesi (ISO-2), IP/ASN'den çözümlenir. ~%99.95 TR. | 
 | CONTINENT_CODE | VARCHAR2 | ✓ |  | İstemci kıtası (örn. AS, EU). | 
 | ASN | VARCHAR2 | ✓ |  | İstemci ağ ASN'si (örn. 47331). Türk Telekom baskın. | 
 | ISP | VARCHAR2 | ✓ |  | İstemci ISS / ağ operatörü (Türk Telekom %47.5, Superonline, Millenicom, Türksat). | 
 | HTTP_HOST | VARCHAR2 | ✓ |  | İstenen sunucu adı (teslim edilen özelliğin sunucu adı). | 

## Keywords

bandwidth, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, usage
## Column Descriptions

- **TIMESTAMP**: Real event time of the request (use this for time filters).
- **Q_TIMESTAMP**: Analytics clock; ~16k rows are 1970-01-01 (invalid) — do NOT use for time filtering.
- **BYTES_SENT**: Total bytes sent to the client (headers + body). Primary bandwidth/data-transfer measure.
- **BODY_BYTES_SENT**: Response body bytes only (excludes headers).
- **REQUEST_TIME**: Total seconds to serve the request — core latency metric.
- **PROXY_CACHE_STATUS**: Cache outcome: HIT (served from edge ~0.045s), MISS (~0.210s), EXPIRED (~0.286s), or empty (non-cacheable). Drives Cache Hit Ratio.
- **STATUS**: HTTP response code. 200 OK (~80%), 410 Gone (~17.5%, benign — expired live-stream segments), 304 Not Modified (~2%). Treat 410 separately from real 5xx errors.
- **SERVER_ROLE**: CDN cache tier that served the request: Node (edge, ~62% hit), Mcache (mid), Feda (fetch-only, 0% hit by design).
- **DATACENTER**: Point of Presence (PoP) that served the request, named city.provider (e.g. ist.mrs = Istanbul). Istanbul PoPs lowest latency (15-26ms); Sydney highest (~275ms).
- **COUNTRY_CODE**: Client country (ISO-2), resolved from IP/ASN. ~99.95% TR.
- **CONTINENT_CODE**: Client continent (e.g. AS, EU).
- **ASN**: Client network ASN (e.g. 47331). Türk Telekom dominates.
- **ISP**: Client ISP / network operator (Türk Telekom 47.5%, Superonline, Millenicom, Türksat).
- **REQUEST_URI**: Requested URI/path (DASH .mpd manifests, HLS .m3u8 playlists, media segments).
- **HTTP_USER_AGENT**: Client user agent — source for device/browser/OS audience attribution.
- **RESOURCE_NAME**: CDN property/resource (e.g. b2metric-video.lg, ssport-live).
- **HTTP_HOST**: Requested host (the delivered property's hostname).
- **ACCOUNT_TYPE**: Customer account tier.
- **TCPINFO_RTT**: TCP round-trip time (network distance signal), microseconds.

### Manual Relationships

- `RESOURCE_NAME` → `DS_PATHA_5M.RESOURCE_NAME` (lookup) — Same property/resource as the 5-min content rollup.
- `DATACENTER` → `DS_BASE_1M.DATACENTER` (lookup) — Same PoP dimension as the 1-min rollup.
## Business Metadata

**Business Name:** Ham CDN Edge İstekleri
**Description:** Medianova CDN edge tarafından sunulan her istek için bir satır içeren ham HTTP erişim günlüğü. Tüm trafik, gecikme, önbellek ve izleyici analizi için temel kaynak. 2026-06-01..2026-06-12 arasını kapsar (7-10 Haziran'da 4 günlük boşluk). Uyarı: 16.127 satırda Q_TIMESTAMP = 1970-01-01 (geçersiz); gerçek olay zamanı için TIMESTAMP kullanın.
**Data Domain:** CDN Dağıtımı
**Business Owner:** Platform / SRE
**Update Frequency:** Streaming (per request)
**Notes:** Tanecik = tek HTTP isteği. ~1.07M satır. Toplu analizler için DS_BASE_1M ve DS_PATHA_5M özetlerini tercih edin; detaylı/forensik sorgular için ALL_RAW kullanın.

### Column Descriptions

- **TIMESTAMP**: İsteğin gerçek olay zamanı (zaman filtreleri için bunu kullanın).
- **Q_TIMESTAMP**: Analitik saati; ~16k satır 1970-01-01 (geçersiz) — zaman filtreleme için KULLANMAYIN.
- **BYTES_SENT**: İstemciye gönderilen toplam bayt (başlıklar + gövde). Birincil bant genişliği/veri aktarımı ölçüsü.
- **BODY_BYTES_SENT**: Yalnızca yanıt gövde baytları (başlıklar hariç).
- **REQUEST_TIME**: İsteği sunmak için geçen toplam saniye — temel gecikme metriği.
- **PROXY_CACHE_STATUS**: Önbellek sonucu: HIT (edge'den sunuldu ~0.045s), MISS (~0.210s), EXPIRED (~0.286s) veya boş (önbelleklenemez). Önbellek İsabet Oranını belirler.
- **STATUS**: HTTP yanıt kodu. 200 OK (~%80), 410 Gone (~%17.5, zararsız — süresi dolmuş canlı yayın segmentleri), 304 Not Modified (~%2). 410'u gerçek 5xx hatalarından ayrı değerlendirin.
- **SERVER_ROLE**: İsteği sunan CDN önbellek katmanı: Node (edge, ~%62 isabet), Mcache (orta), Feda (sadece getir, tasarım gereği %0 isabet).
- **DATACENTER**: İsteği sunan uç nokta (PoP), şehir.sağlayıcı olarak adlandırılır (örn. ist.mrs = İstanbul). İstanbul PoP'leri en düşük gecikme (15-26ms); Sidney en yüksek (~275ms).
- **COUNTRY_CODE**: İstemci ülkesi (ISO-2), IP/ASN'den çözümlenir. ~%99.95 TR.
- **CONTINENT_CODE**: İstemci kıtası (örn. AS, EU).
- **ASN**: İstemci ağ ASN'si (örn. 47331). Türk Telekom baskın.
- **ISP**: İstemci ISS / ağ operatörü (Türk Telekom %47.5, Superonline, Millenicom, Türksat).
- **REQUEST_URI**: İstenen URI/yol (DASH .mpd manifestleri, HLS .m3u8 oynatma listeleri, medya segmentleri).
- **HTTP_USER_AGENT**: İstemci kullanıcı aracısı — cihaz/tarayıcı/işletim sistemi izleyici ilişkilendirmesi için kaynak.
- **RESOURCE_NAME**: CDN özelliği/kaynağı (örn. b2metric-video.lg, ssport-live).
- **HTTP_HOST**: İstenen sunucu adı (teslim edilen özelliğin sunucu adı).
- **ACCOUNT_TYPE**: Müşteri hesap katmanı.
- **TCPINFO_RTT**: TCP gidiş-dönüş süresi (ağ mesafesi sinyali), mikrosaniye.

### Manual Relationships

- `RESOURCE_NAME` → `DS_PATHA_5M.RESOURCE_NAME` (lookup) — Same property/resource as the 5-min content rollup.
- `DATACENTER` → `DS_BASE_1M.DATACENTER` (lookup) — Same PoP dimension as the 1-min rollup.
