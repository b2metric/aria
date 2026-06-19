---
table: ALL_RAW
database: oracle
workspace: medianova
keywords: [access log, bandwidth, cdn, country, data, date, demographic, edge, geography,
  internet, istek, lifecycle, log, nationality, raw, request, state, status, temporal,
  time, traffic, usage]
generated_at: 2026-06-19 08:10:39.174474+00:00
description: 'Raw HTTP access log — one row per request served by the Medianova CDN
  edge. Source of truth for all traffic, latency, cache and audience analysis. Spans
  2026-06-01..2026-06-12 (4-day gap Jun 7-10). Caveat: 16,127 rows have Q_TIMESTAMP
  = 1970-01-01 (invalid); use TIMESTAMP for real event time.'
business_name: Raw CDN Edge Requests
data_domain: CDN Delivery
enriched_at: '2026-06-19T08:13:29.272401+00:00'
---

# ALL_RAW

**Description:** Table containing All Raw data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | Q_TIMESTAMP | TIMESTAMP(6) | ✓ |  | Analytics clock; ~16k rows are 1970-01-01 (invalid) — do NOT use for time filtering. | 
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Cache outcome: HIT (served from edge ~0.045s), MISS (~0.210s), EXPIRED (~0.286s), or empty (non-cacheable). Drives Cache Hit Ratio. | 
 | TIMESTAMP | TIMESTAMP(6) | ✓ |  | Real event time of the request (use this for time filters). | 
| REMOTE_ADDR | VARCHAR2 | ✓ |  | Remote Addr |
| REMOTE_PORT | VARCHAR2 | ✓ |  | Remote Port |
| REQUEST_ADDR | VARCHAR2 | ✓ |  | Request Addr |
| SERVER_NAME | VARCHAR2 | ✓ |  | Server Name |
| SERVER_PORT | NUMBER | ✓ |  | Server Port |
 | BODY_BYTES_SENT | NUMBER | ✓ |  | Response body bytes only (excludes headers). | 
 | BYTES_SENT | NUMBER | ✓ |  | Total bytes sent to the client (headers + body). Primary bandwidth/data-transfer measure. | 
| BODY_RECEIVED | NUMBER | ✓ |  | Body Received |
 | REQUEST_TIME | NUMBER | ✓ |  | Total seconds to serve the request — core latency metric. | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP response code. 200 OK (~80%), 410 Gone (~17.5%, benign — expired live-stream segments), 304 Not Modified (~2%). Treat 410 separately from real 5xx errors. | 
 | REQUEST_URI | VARCHAR2 | ✓ |  | Requested URI/path (DASH .mpd manifests, HLS .m3u8 playlists, media segments). | 
| REQUEST_PARAM | VARCHAR2 | ✓ |  | Request Param |
| REQUEST_METHOD | VARCHAR2 | ✓ |  | Request Method |
| UPSTREAM_ADDR | VARCHAR2 | ✓ |  | Upstream Addr |
| UPSTREAM_RESPONSE_TIME | NUMBER | ✓ |  | Upstream Response Time |
| UPSTREAM_CONNECT_TIME | NUMBER | ✓ |  | Upstream Connect Time |
| UPSTREAM_HEADER_TIME | NUMBER | ✓ |  | Upstream Header Time |
| UPSTREAM_STATUS | VARCHAR2 | ✓ |  | Upstream Status |
| SCHEME | VARCHAR2 | ✓ |  | Scheme |
| HTTP_REFERRER | VARCHAR2 | ✓ |  | Http Referrer |
 | TCPINFO_RTT | VARCHAR2 | ✓ |  | TCP round-trip time (network distance signal), microseconds. | 
| TCPINFO_RTTVAR | VARCHAR2 | ✓ |  | Tcpinfo Rttvar |
| SSL_PROTOCOL | VARCHAR2 | ✓ |  | Ssl Protocol |
| SSL_CIPHER | VARCHAR2 | ✓ |  | Ssl Cipher |
| REQUEST_ID | VARCHAR2 | ✓ |  | Request Id |
| ROLE | VARCHAR2 | ✓ |  | Role |
| HTTP_RANGE | VARCHAR2 | ✓ |  | Http Range |
 | ACCOUNT_TYPE | VARCHAR2 | ✓ |  | Customer account tier. | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | CDN cache tier that served the request: Node (edge, ~62% hit), Mcache (mid), Feda (fetch-only, 0% hit by design). | 
| HTTP_X_FORWARDED_FOR | VARCHAR2 | ✓ |  | Http X Forwarded For |
| HTTP_PROTOCOL | VARCHAR2 | ✓ |  | Http Protocol |
 | RESOURCE_NAME | VARCHAR2 | ✓ |  | CDN property/resource (e.g. b2metric-video.lg, ssport-live). | 
| ORG_NAME | VARCHAR2 | ✓ |  | Org Name |
| RESOURCE_UUID | VARCHAR2 | ✓ |  | Resource Uuid |
 | HTTP_USER_AGENT | VARCHAR2 | ✓ |  | Client user agent — source for device/browser/OS audience attribution. | 
| HOST_ROLE | VARCHAR2 | ✓ |  | Host Role |
| TENANT_CODE | VARCHAR2 | ✓ |  | Tenant Code |
 | DATACENTER | VARCHAR2 | ✓ |  | Point of Presence (PoP) that served the request, named city.provider (e.g. ist.mrs = Istanbul). Istanbul PoPs lowest latency (15-26ms); Sydney highest (~275ms). | 
| CDN_ROLE | VARCHAR2 | ✓ |  | Cdn Role |
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | Client country (ISO-2), resolved from IP/ASN. ~99.95% TR. | 
 | CONTINENT_CODE | VARCHAR2 | ✓ |  | Client continent (e.g. AS, EU). | 
 | ASN | VARCHAR2 | ✓ |  | Client network ASN (e.g. 47331). Türk Telekom dominates. | 
 | ISP | VARCHAR2 | ✓ |  | Client ISP / network operator (Türk Telekom 47.5%, Superonline, Millenicom, Türksat). | 
 | HTTP_HOST | VARCHAR2 | ✓ |  | Requested host (the delivered property's hostname). | 

## Keywords

bandwidth, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, usage
## Business Metadata

**Business Name:** Raw CDN Edge Requests
**Description:** Raw HTTP access log — one row per request served by the Medianova CDN edge. Source of truth for all traffic, latency, cache and audience analysis. Spans 2026-06-01..2026-06-12 (4-day gap Jun 7-10). Caveat: 16,127 rows have Q_TIMESTAMP = 1970-01-01 (invalid); use TIMESTAMP for real event time.
**Data Domain:** CDN Delivery
**Business Owner:** Platform / SRE
**Update Frequency:** Streaming (per request)
**Notes:** Grain = single HTTP request. ~1.07M rows. Prefer the rollups (DS_BASE_1M, DS_PATHA_5M) for aggregate analytics; use ALL_RAW for drill-down / forensic queries.

### Column Descriptions

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
