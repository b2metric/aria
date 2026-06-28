---
table: DS_BASE_1M
database: oracle
workspace: medianova
keywords: [1 minute, aggregate, bandwidth, cache hit ratio, cache tier, country, data,
  date, demographic, edge, feda, geography, internet, latency, lifecycle, mcache,
  metrics, metrik, nationality, node, rollup, state, status, temporal, time, traffic,
  usage, uç, önbellek isabet oranı, önbellek katmanı, özet]
generated_at: 2026-06-19 08:10:39.175188+00:00
description: CDN trafiğinin dakika başına toplamı, org/sunucu/sunucuadı/hesap/ülke/sunucurolü/verimerkezi/önbellekdurumu/durum/asn'e
  göre gruplandırılmıştır. Trafik, bant genişliği, önbellek isabet oranı, gecikme
  ve RTT trendleri için başvurulan tablo. ~91.6k satır.
business_name: CDN Metrikleri — 1 Dakikalık Özet
data_domain: CDN Dağıtımı
enriched_at: '2026-06-19T13:10:53.228380+00:00'
---

# DS_BASE_1M

**Description:** Table containing Ds Base 1M data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | START_DATE | TIMESTAMP(6) | ✓ |  | 1 dakikalık kovanın başlangıcı (zaman serisi için kullanın). | 
 | ORG_NAME | VARCHAR2 | ✓ |  | Kuruluş / kiracı. | 
 | SERVER_NAME | VARCHAR2 | ✓ |  | Edge sunucu FQDN'si. | 
 | HTTP_HOST | VARCHAR2 | ✓ |  | Teslim edilen sunucu adı. | 
 | ACCOUNT_TYPE | VARCHAR2 | ✓ |  | Müşteri hesap katmanı. | 
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | İstemci ülkesi (ISO-2). | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | Önbellek katmanı (cache tier). Değerler SADECE: 'Node' (= Edge / uç katman), 'Mcache' (orta katman), 'Feda' (origin-fetch). Edge/uç katmanı sorulduğunda SERVER_ROLE='Node' ile filtrele. | 
 | DATACENTER | VARCHAR2 | ✓ |  | Trafiği sunan PoP (şehir.sağlayıcı). | 
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Önbellek sonucu. Değerler SADECE: 'HIT', 'MISS', 'EXPIRED', '' (boş = önbelleklenemez). Başka değer YOKTUR (STALE_HIT yoktur). İsabet = PROXY_CACHE_STATUS='HIT'. | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP durum kodu gruplaması (200/410/304/...). | 
 | ASN | VARCHAR2 | ✓ |  | İstemci ağ ASN'si. | 
 | REQUEST_NUMBER | NUMBER | ✓ |  | Kovadaki istek sayısı — İstek hacmi metriği. | 
 | BYTES_SENT | NUMBER | ✓ |  | Kovada teslim edilen toplam bayt — Bant genişliği / veri aktarımı. | 
 | AVG_REQUEST_TIME | NUMBER | ✓ |  | Kova için ortalama istek gecikmesi (saniye). | 
 | AVG_TCPINFO_RTT | NUMBER | ✓ |  | Ortalama TCP gidiş-dönüş süresi (mikrosaniye) — ağ mesafesi. | 
| REQUEST_TIME_QUANTILES_P25 | NUMBER | ✓ |  | Request Time Quantiles P25 |
 | REQUEST_TIME_QUANTILES_P50 | NUMBER | ✓ |  | Medyan istek gecikmesi (p50), saniye. | 
| REQUEST_TIME_QUANTILES_P75 | NUMBER | ✓ |  | Request Time Quantiles P75 |
| REQUEST_TIME_QUANTILES_P90 | NUMBER | ✓ |  | Request Time Quantiles P90 |
 | REQUEST_TIME_QUANTILES_P95 | NUMBER | ✓ |  | %95. yüzdelik istek gecikmesi (kuyruk gecikmesi). | 
 | REQUEST_TIME_QUANTILES_P99 | NUMBER | ✓ |  | %99. yüzdelik istek gecikmesi (en kötü durum kuyruğu). | 

## Keywords

bandwidth, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, usage
## Business Metadata

**Notes:** Önbellek İsabet Oranı = SUM(REQUEST_NUMBER) WHERE PROXY_CACHE_STATUS='HIT' / SUM(REQUEST_NUMBER). Edge/uç katmanı = SERVER_ROLE='Node'.

## Column Descriptions

- **START_DATE**: Start of the 1-minute bucket (use for time series).
- **REQUEST_NUMBER**: Number of requests in the bucket — the Requests volume metric.
- **BYTES_SENT**: Total bytes delivered in the bucket — Bandwidth / data transfer.
- **AVG_REQUEST_TIME**: Average request latency (seconds) for the bucket.
- **AVG_TCPINFO_RTT**: Average TCP round-trip time (microseconds) — network distance.
- **REQUEST_TIME_QUANTILES_P50**: Median request latency (p50), seconds.
- **REQUEST_TIME_QUANTILES_P95**: 95th percentile request latency (tail latency).
- **REQUEST_TIME_QUANTILES_P99**: 99th percentile request latency (worst-case tail).
- **PROXY_CACHE_STATUS**: Cache outcome for the grouped rows (HIT/MISS/EXPIRED/empty). Used for Cache Hit Ratio.
- **SERVER_ROLE**: Cache tier (Node/Mcache/Feda).
- **DATACENTER**: PoP that served the traffic (city.provider).
- **COUNTRY_CODE**: Client country (ISO-2).
- **STATUS**: HTTP status code grouping (200/410/304/...).
- **ASN**: Client network ASN.
- **ORG_NAME**: Organization / tenant.
- **SERVER_NAME**: Edge server FQDN.
- **HTTP_HOST**: Delivered host.
- **ACCOUNT_TYPE**: Customer account tier.

## Relationships

- `DATACENTER` → `ALL_RAW.DATACENTER` (lookup) — Aggregated from the raw request log.
