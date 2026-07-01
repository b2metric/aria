# Vault rebuild from a remote Oracle snapshot (runbook)

Rebuild a customer's ARIA vault (dtypes / enums / relationships) from a fresh pull
of their **remote** Oracle DB, while **preserving curated content** (descriptions,
Example Queries, Domain Mapping, Business Metadata, `join_keys.json`).

Worked example below is **stc-kuwait** (10 active tables). Two scripts:

| Script | Runs on | Needs |
|--------|---------|-------|
| `scripts/vault-extract-remote.py` | a box that can reach the **remote Oracle** | `oracledb` (+ `pyarrow` for Parquet) |
| `scripts/vault-replace-from-metadata.py` | inside the **ARIA repo** (vault files on disk) | the ARIA venv (`uv`) |

> Why not just POST the JSON to `/api/workspaces/vault/import-metadata`? That path
> is *additive* — for a table that already has a vault file it refreshes enums +
> descriptions but does **not** replace column dtypes. The replacer does the true
> "replace structure, keep curation". Use the API import only when you want an
> enum/description top-up without a dtype refresh.

---

## Phase 1 — extract on the remote box

Stage dependencies (pure-Python wheels, air-gap friendly):

```bash
# on an internet machine:
pip download oracledb pyarrow -d ./wheels --only-binary=:all:
# copy ./wheels + scripts/vault-extract-remote.py + scripts/active_tables-stc-kuwait.txt over, then:
pip install --no-index --find-links ./wheels oracledb pyarrow
```

Run the extractor (only the active tables). Credentials fall back to env vars
(`ORA_HOST/ORA_PORT/ORA_SERVICE/ORA_USER/ORA_PASSWORD/ORA_OWNER`) so the password
need not appear in `argv`:

```bash
export ORA_PASSWORD='***'
python vault-extract-remote.py \
    --host MIS-DWH.STC.COM.KW --port 1521 --service stcdw \
    --user COMMBI_PROD --owner COMMBI_PROD \
    --tables-file active_tables-stc-kuwait.txt \
    --out-dir ./stc-vault-snapshot \
    --sample-rows 20 --max-cardinality 50
```

Captures, per table: columns (name / dtype / nullable / PK), low-cardinality enum
DISTINCT values, FK relationships, row-count estimate, the object's own
materialized-view/view SQL (if it is one), and sample rows. It also scans for
**views / materialized views that depend on** the tables and captures their SQL.

Outputs in `--out-dir`:
- `db-metadata-<owner>-<ts>.json` — the full snapshot (import-compatible shape).
- `parquet/<TABLE>.parquet` — per-table sample rows (needs `pyarrow`).
- `manifest.json` — summary + counts + error count.

> ⚠️ **PII:** with `--sample-rows > 0` the artifacts contain real row values. Keep
> them internal. Sample rows are **never** written into the vault. Use
> `--sample-rows 0` to skip them entirely.

### Thick mode (legacy password verifier → DPY-3015)

If the connection fails with `DPY-3015: password verifier type 0x939 is not
supported ... in thin mode`, the DB user has an old **10G** password verifier that
thin mode cannot use. Run in **thick mode** with the Oracle Instant Client:

```bash
# macOS ARM (Apple Silicon): download "Instant Client Basic" ARM64 from Oracle,
# unzip, then clear the Gatekeeper quarantine:
xattr -r -d com.apple.quarantine ~/oracle/instantclient_23_3

python vault-extract-remote.py --thick --lib-dir ~/oracle/instantclient_23_3 \
    --host MIS-DWH.STC.COM.KW --port 1521 --service stcdw \
    --user COMMBI_PROD --owner COMMBI_PROD \
    --tables-file active_tables-stc-kuwait.txt --out-dir ./stc-vault-snapshot
```

`--lib-dir` can be omitted (or set `ORA_LIB_DIR`) if the client libs are already
on the default search path. Everything else about the run is identical.

Copy `--out-dir` back to a machine with the ARIA repo.

---

## Phase 2 — rebuild the vault (in the ARIA repo)

**Dry-run first** (default) — writes rebuilt files to `./vault-preview/` and
validates them without touching the live vault:

```bash
uv run python scripts/vault-replace-from-metadata.py \
    --workspace stc-kuwait \
    --json ./stc-vault-snapshot/db-metadata-commbi_prod-<ts>.json \
    --validate
```

Review `./vault-preview/*.md` (diff against `docs/vaults/stc-kuwait/tables/`).
Confirm: dtypes refreshed, enum blocks updated, `## Example Queries` /
`## Domain Mapping` / descriptions intact.

**Apply in place** once satisfied:

```bash
uv run python scripts/vault-replace-from-metadata.py \
    --workspace stc-kuwait \
    --json ./stc-vault-snapshot/db-metadata-commbi_prod-<ts>.json \
    --apply --validate
```

Then **re-index Qdrant** so retrieval picks up the changes — re-run vault sync /
generate for the workspace, or restart the backend (the vault→Qdrant index is a
derived, SHA-idempotent cache, rebuilt from the markdown).

Finally, commit the changed `docs/vaults/stc-kuwait/tables/*.md`.

---

## What is preserved vs regenerated

| Vault content | On rebuild |
|---------------|------------|
| frontmatter `description`, `keywords`, `business_name`, `data_domain` | **preserved** (when the old file had it) |
| per-column descriptions (matched by name) | **preserved**, carried into the new Columns table |
| `## Example Queries`, `## Domain Mapping`, `## Business Metadata` | **preserved** verbatim |
| `join_keys.json` | **untouched** |
| `## Columns` (dtype / nullable / PK) | **regenerated** from fresh metadata |
| `## Sampled Values` enum block | **regenerated** from fresh DISTINCT values |
| `## Relationships` | **regenerated** from fresh FKs (empty if the DB has no FKs — curated joins live in `join_keys.json`) |
| columns dropped in the source DB | **removed**; new columns **added** |

Useful flags: `--only TABLE1,TABLE2` (subset), `--preview-dir PATH`,
`--vault-root PATH`.

---

## Alternative — enum/description top-up only (no dtype refresh)

If you only need to refresh enums + push descriptions (not dtypes), the existing
transport works without the replacer:

```bash
python scripts/vault-upload.py --json <metadata.json>   # Keycloak auth + multipart
# → POST /api/workspaces/vault/import-metadata  (workspace derived from the JWT)
```
