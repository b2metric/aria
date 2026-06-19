---
table: DS_BASE_1M
database: oracle
workspace: medianova
keywords: [1 minute, aggregate, bandwidth, cache hit ratio, country, data, date, demographic,
  geography, internet, latency, lifecycle, metrics, metrik, nationality, rollup, state,
  status, temporal, time, traffic, usage, özet]
generated_at: 2026-06-19 08:10:39.175188+00:00
description: Per-minute aggregate of CDN traffic, grouped by org/server/host/account/country/server_role/datacenter/cache_status/status/asn.
  The go-to table for traffic, bandwidth, cache-hit-ratio, latency and RTT trends.
  ~91.6k rows.
business_name: CDN Metrics — 1-Minute Rollup
data_domain: CDN Delivery
enriched_at: '2026-06-19T08:13:29.274374+00:00'
---

# DS_BASE_1M

**Description:** Table containing Ds Base 1M data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | START_DATE | TIMESTAMP(6) | ✓ |  | Start of the 1-minute bucket (use for time series). | 
 | ORG_NAME | VARCHAR2 | ✓ |  | Organization / tenant. | 
 | SERVER_NAME | VARCHAR2 | ✓ |  | Edge server FQDN. | 
 | HTTP_HOST | VARCHAR2 | ✓ |  | Delivered host. | 
 | ACCOUNT_TYPE | VARCHAR2 | ✓ |  | Customer account tier. | 
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | Client country (ISO-2). | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | Cache tier (Node/Mcache/Feda). | 
 | DATACENTER | VARCHAR2 | ✓ |  | PoP that served the traffic (city.provider). | 
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Cache outcome for the grouped rows (HIT/MISS/EXPIRED/empty). Used for Cache Hit Ratio. | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP status code grouping (200/410/304/...). | 
 | ASN | VARCHAR2 | ✓ |  | Client network ASN. | 
 | REQUEST_NUMBER | NUMBER | ✓ |  | Number of requests in the bucket — the Requests volume metric. | 
 | BYTES_SENT | NUMBER | ✓ |  | Total bytes delivered in the bucket — Bandwidth / data transfer. | 
 | AVG_REQUEST_TIME | NUMBER | ✓ |  | Average request latency (seconds) for the bucket. | 
 | AVG_TCPINFO_RTT | NUMBER | ✓ |  | Average TCP round-trip time (microseconds) — network distance. | 
| REQUEST_TIME_QUANTILES_P25 | NUMBER | ✓ |  | Request Time Quantiles P25 |
 | REQUEST_TIME_QUANTILES_P50 | NUMBER | ✓ |  | Median request latency (p50), seconds. | 
| REQUEST_TIME_QUANTILES_P75 | NUMBER | ✓ |  | Request Time Quantiles P75 |
| REQUEST_TIME_QUANTILES_P90 | NUMBER | ✓ |  | Request Time Quantiles P90 |
 | REQUEST_TIME_QUANTILES_P95 | NUMBER | ✓ |  | 95th percentile request latency (tail latency). | 
 | REQUEST_TIME_QUANTILES_P99 | NUMBER | ✓ |  | 99th percentile request latency (worst-case tail). | 

## Keywords

bandwidth, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, usage
## Business Metadata

**Business Name:** CDN Metrics — 1-Minute Rollup
**Description:** Per-minute aggregate of CDN traffic, grouped by org/server/host/account/country/server_role/datacenter/cache_status/status/asn. The go-to table for traffic, bandwidth, cache-hit-ratio, latency and RTT trends. ~91.6k rows.
**Data Domain:** CDN Delivery
**Business Owner:** Analytics
**Update Frequency:** 1-minute batches
**Notes:** Latency stored both as an average (AVG_REQUEST_TIME) and tDigest quantiles (p25..p99). Cache Hit Ratio = SUM(REQUEST_NUMBER) where PROXY_CACHE_STATUS='HIT' / SUM(REQUEST_NUMBER).

### Column Descriptions

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

### Manual Relationships

- `DATACENTER` → `ALL_RAW.DATACENTER` (lookup) — Aggregated from the raw request log.
