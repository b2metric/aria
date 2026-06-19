---
table: DS_PATHA_5M
database: oracle
workspace: medianova
keywords: [5 minute, acquisition, audience, bandwidth, browser, channel, content,
  country, data, date, demographic, device, geography, internet, izleyici, içerik,
  kitle, lifecycle, nationality, referrer, rollup, state, status, temporal, time,
  touchpoint, uri, usage]
generated_at: 2026-06-19 08:10:39.175641+00:00
description: Per-5-minute aggregate keyed by content path and audience, grouped by
  org/server/resource/host/cache_status/status/referrer/country/uri_path/device/browser/os/app.
  The table for content (URI), audience (device/browser/OS) and referrer analytics.
  ~498.5k rows.
business_name: CDN Content & Audience — 5-Minute Rollup
data_domain: CDN Content & Audience
enriched_at: '2026-06-19T08:13:29.275473+00:00'
---

# DS_PATHA_5M

**Description:** Table containing Ds Patha 5M data

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
 | START_DATE | TIMESTAMP(6) | ✓ |  | Start of the 5-minute bucket. | 
| ORG_NAME | VARCHAR2 | ✓ |  | Org Name |
| SERVER_NAME | VARCHAR2 | ✓ |  | Server Name |
 | RESOURCE_NAME | VARCHAR2 | ✓ |  | CDN property/resource. | 
| HTTP_HOST | VARCHAR2 | ✓ |  | Http Host |
 | PROXY_CACHE_STATUS | VARCHAR2 | ✓ |  | Cache outcome (HIT/MISS/EXPIRED/empty). | 
 | STATUS | VARCHAR2 | ✓ |  | HTTP status code. | 
 | HTTP_REFERRER | VARCHAR2 | ✓ |  | Referring site/app (e.g. app.b2metric.com). | 
 | COUNTRY_CODE | VARCHAR2 | ✓ |  | Client country (ISO-2). | 
 | URI_PATH | VARCHAR2 | ✓ |  | Content path requested (channel manifests/playlists/segments). Group by this for top-content analysis. | 
| HTTP_USER_AGENT | VARCHAR2 | ✓ |  | Http User Agent |
 | DEVICE_TYPE | VARCHAR2 | ✓ |  | Audience device: Desktop, Mobile, Tablet (derived from user agent). | 
 | BROWSER_FAMILY | VARCHAR2 | ✓ |  | Audience browser family (Chrome, Safari, AppleCoreMedia, ...). | 
 | OS_FAMILY | VARCHAR2 | ✓ |  | Audience OS family (Android, iOS, Windows, MacOS, ...). Android largest. | 
 | APP_FAMILY | VARCHAR2 | ✓ |  | Application family (Browser, AppleCoreMedia). | 
 | REQUEST_NUMBER | NUMBER | ✓ |  | Requests in the bucket — Requests metric. | 
 | BYTES_SENT | NUMBER | ✓ |  | Total bytes delivered — Bandwidth. | 
 | BODY_BYTES_SENT | NUMBER | ✓ |  | Response body bytes (payload). | 
 | AVG_REQUEST_TIME | NUMBER | ✓ |  | Average request latency (seconds). | 
 | SERVER_ROLE | VARCHAR2 | ✓ |  | Cache tier (Node/Mcache/Feda). | 

## Keywords

acquisition, bandwidth, channel, country, data, date, demographic, geography, internet, lifecycle, nationality, state, status, temporal, time, touchpoint, usage
## Business Metadata

**Business Name:** CDN Content & Audience — 5-Minute Rollup
**Description:** Per-5-minute aggregate keyed by content path and audience, grouped by org/server/resource/host/cache_status/status/referrer/country/uri_path/device/browser/os/app. The table for content (URI), audience (device/browser/OS) and referrer analytics. ~498.5k rows.
**Data Domain:** CDN Content & Audience
**Business Owner:** Analytics / Product
**Update Frequency:** 5-minute batches
**Notes:** Use for 'top URLs/channels by bytes', device/browser/OS splits, and referrer analysis. Manifests (.mpd) = high request count, low bytes; media (.m3u8/segments) = high bytes.

### Column Descriptions

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

### Manual Relationships

- `RESOURCE_NAME` → `ALL_RAW.RESOURCE_NAME` (lookup) — Aggregated from the raw request log.
