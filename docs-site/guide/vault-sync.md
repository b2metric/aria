# Vault Auto-Sync

The **semantic vault** is how ARIA understands your tables in business terms. It is generated
automatically during onboarding **sync** and refreshed whenever you re-sync.

- On register/connect, ARIA discovers your schema and writes vault topics (keywords, descriptions,
  example queries) per table.
- Re-syncing **preserves your manual edits** (keywords, column descriptions) for tables that still exist.
- The vault is ingested into Qdrant so questions retrieve the right tables.

See it in action: [Connecting Your Data](./onboarding.md).
