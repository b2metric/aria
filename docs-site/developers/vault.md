# Semantic Vault

The vault is the **schema-semantics layer** that lets ARIA map a business question to the right
tables/columns without hard-coded SQL — adapted per customer **without writing code**.

Each topic is a markdown file with frontmatter: `keywords`, `domain`, `topic`, `order`, `insights`,
`relationships`, plus per-column descriptions and example queries. Synced to Qdrant for retrieval.

> Source-of-truth: `docs/vault-schema.md`. Vault files are generated/refreshed during onboarding sync.
