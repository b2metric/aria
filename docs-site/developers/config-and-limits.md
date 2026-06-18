# Configuration & Limits

Operational governance knobs (admin-configurable per customer).

| Area | What | Source |
|---|---|---|
| **Row limit** | Default 10K rows/query; overflow → background report + timed MinIO link | `backend/app/core/config.py`, `db/executor.py` |
| **Token quota** | 3 tiers — session (100K) / user (500K) / team (2M); local LLMs counted | `models/token.py`, `services/token.py` |
| **SQL visibility** | Role-based: admin/team_lead/analyst see SQL + raw rows; viewer sees answer + chart only | RBAC |
| **BYOK** | Per-customer LLM provider key (planned) | `services/llm_resolver.py` |
| **CMEK** | Per-customer data-at-rest encryption key (planned) | `services/crypto.py`, `services/kms/` |
| **Roles** | admin · team_lead · analyst · viewer (Keycloak) | `auth/` |

> Source-of-truth: `backend/app/core/config.py`. Sync via the `update-docs` skill.
