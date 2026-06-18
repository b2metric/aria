# Row Limits & Safeguards

To keep queries safe and fast, ARIA caps how many rows a single query returns.

- **Default 10,000 rows** per query (admin-configurable under **Tenant Configuration**).
- **Overflow** large results are generated in the background and delivered as a **time-limited
  download link** (MinIO, ~3 days) instead of flooding the UI.
- Unauthorized attempts to exceed the limit are blocked.
