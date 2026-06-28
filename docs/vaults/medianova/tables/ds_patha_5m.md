---
table: DS_PATHA_5M
database: oracle
workspace: medianova
keywords: [5 minute, acquisition, audience, bandwidth, browser, channel, content,
  country, data, date, demographic, device, geography, internet, izleyici, içerik,
  kitle, lifecycle, nationality, referrer, rollup, state, status, temporal, time,
  touchpoint, uri, usage]
generated_at: 2026-06-19 08:10:39.175641+00:00
description: İçerik yolu ve izleyiciye göre anahtarlanmış 5 dakikalık toplam, org/sunucu/kaynak/sunucuadı/önbellekdurumu/durum/yönlendiren/ülke/uri_yolu/cihaz/tarayıcı/işletimsistemi/uygulama'ya
  göre gruplandırılmıştır. İçerik (URI), izleyici (cihaz/tarayıcı/işletim sistemi)
  ve yönlendiren analitiği için tablo. ~498.5k satır.
business_name: CDN İçerik ve İzleyici — 5 Dakikalık Özet
data_domain: CDN İçerik ve İzleyici
enriched_at: '2026-06-19T09:35:41.380338+00:00'
---

# DS_PATHA_5M

**Description:** Table containing Ds Patha 5M data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | START_DATE | TIMESTAMP(6) | ✓ |  | 5 dakikalık kovanın başlangıcı. | 
| ORG_NAME | VARCHAR2 | ✓ |  | Org Name |
| SERVER_NAME | VARCHAR2 | ✓ |  | Server Name |
 | RESOURCE_NAME | VARCHAR2 | ✓ |  | CDN özelliği/kaynağı. | 
| HTTP_HOST | VARCHAR2 | ✓ |  | Http Host |
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Önbellek sonucu (HIT/MISS/EXPIRED/boş). | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP durum kodu. | 
 | HTTP_REFERRER | VARCHAR2 | ✓ |  | Yönlendiren site/uygulama (örn. app.b2metric.com). | 
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | İstemci ülkesi (ISO-2). | 
 | URI_PATH | VARCHAR2 | ✓ |  | İstenen içerik yolu (kanal manifestleri/oynatma listeleri/segmentler). En iyi içerik analizi için buna göre gruplandırın. | 
| HTTP_USER_AGENT | VARCHAR2 | ✓ |  | Http User Agent |
 | DEVICE_TYPE | VARCHAR2 | ✓ |  | İzleyici cihazı: Desktop, Mobil, Tablet (kullanıcı aracısından türetilmiştir). | 
 | BROWSER_FAMILY | VARCHAR2 | ✓ |  | İzleyici tarayıcı ailesi (Chrome, Safari, AppleCoreMedia, ...). | 
 | OS_FAMILY | VARCHAR2 | ✓ |  | İzleyici işletim sistemi ailesi (Android, iOS, Windows, MacOS, ...). Android en büyük. | 
 | APP_FAMILY | VARCHAR2 | ✓ |  | Uygulama ailesi (Browser, AppleCoreMedia). | 
 | REQUEST_NUMBER | NUMBER | ✓ |  | Kovadaki istekler — İstek metriği. | 
 | BYTES_SENT | NUMBER | ✓ |  | Teslim edilen toplam bayt — Bant genişliği. | 
 | BODY_BYTES_SENT | NUMBER | ✓ |  | Yanıt gövde baytları (yük). | 
 | AVG_REQUEST_TIME | NUMBER | ✓ |  | Ortalama istek gecikmesi (saniye). | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | Önbellek katmanı (Node/Mcache/Feda). | 

## Keywords

acquisition, bandwidth, channel, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, touchpoint, usage
## Business Metadata

**Business Name:** CDN İçerik ve İzleyici — 5 Dakikalık Özet
**Description:** İçerik yolu ve izleyiciye göre anahtarlanmış 5 dakikalık toplam, org/sunucu/kaynak/sunucuadı/önbellekdurumu/durum/yönlendiren/ülke/uri_yolu/cihaz/tarayıcı/işletimsistemi/uygulama'ya göre gruplandırılmıştır. İçerik (URI), izleyici (cihaz/tarayıcı/işletim sistemi) ve yönlendiren analitiği için tablo. ~498.5k satır.
**Data Domain:** CDN İçerik ve İzleyici
**Business Owner:** Analytics / Product
**Update Frequency:** 5-minute batches
**Notes:** 'Bayta göre en iyi URL'ler/kanallar', cihaz/tarayıcı/işletim sistemi dağılımları ve yönlendiren analizi için kullanın. Manifestler (.mpd) = yüksek istek sayısı, düşük bayt; medya (.m3u8/segmentler) = yüksek bayt.

## Column Descriptions

- **START_DATE**: Start of the 5-minute bucket.
- **URI_PATH**: Content path requested (channel manifests/playlists/segments). Group by this for top-content analysis.
- **REQUEST_NUMBER**: Requests in the bucket — Requests metric.
- **BYTES_SENT**: Total bytes delivered — Bandwidth.
- **BODY_BYTES_SENT**: Response body bytes (payload).
- **AVG_REQUEST_TIME**: Average request latency (seconds).
- **DEVICE_TYPE**: Audience device: Desktop, Mobile, Tablet (derived from user agent).
- **BROWSER_FAMILY**: Audience browser family (Chrome, Safari, AppleCoreMedia, ...).
- **OS_FAMILY**: Audience OS family (Android, iOS, Windows, MacOS, ...). Android largest.
- **APP_FAMILY**: Application family (Browser, AppleCoreMedia).
- **HTTP_REFERRER**: Referring site/app (e.g. app.b2metric.com).
- **PROXY_CACHE_STATUS**: Cache outcome (HIT/MISS/EXPIRED/empty).
- **STATUS**: HTTP status code.
- **COUNTRY_CODE**: Client country (ISO-2).
- **RESOURCE_NAME**: CDN property/resource.
- **SERVER_ROLE**: Cache tier (Node/Mcache/Feda).

## Relationships

- `RESOURCE_NAME` → `ALL_RAW.RESOURCE_NAME` (lookup) — Aggregated from the raw request log.
