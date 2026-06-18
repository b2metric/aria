# CMEK & Envelope Encryption

**CMEK** (Customer-Managed Encryption Key) lets you hold your own data-at-rest key. ARIA uses
**envelope encryption**: each customer's secrets are encrypted with a per-customer **DEK** (data
key), and that DEK is **wrapped** by a **KEK** (key-encryption key) that you control in your own KMS
(e.g. Azure Key Vault).

**Why it matters**
- **Crypto-shredding:** revoke your KEK and the data becomes permanently unrecoverable — instant,
  provable erasure (KVKK / GDPR right-to-erasure).
- **Rotation:** rotating the KEK re-wraps the DEK cheaply; your stored data is untouched.

Set the key provider under **Settings → Encryption**.
