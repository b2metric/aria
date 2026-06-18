# Data Exports (MinIO)

When a result is large or you want it offline, ARIA produces an export artifact.

- Big result sets (over the row limit) are generated in the background and stored in **MinIO**.
- You receive a **time-limited download link** (~3 days) — secure and self-expiring.
- Exports respect your role and the same access policies as live queries.
