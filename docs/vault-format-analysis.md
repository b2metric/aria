# Vault Format Analysis & Schema Contract

> **Status:** authority for the vault's information architecture.
> **Date:** 2026-06-28 · **Branch:** feat/sprint16-hygiene
> **TL;DR:** the vault is *Obsidian-flavored markdown*, not a real Obsidian vault and
> not a real semantic layer. The format is fine; the **lack of an enforced contract**
> is what let it drift (duplicated sections, stale placeholders, empty descriptions).
> We keep the markdown substrate, adopt a semantic-layer *information architecture*
> (one concern per section, single source of truth), and enforce it with
> [`scripts/validate-vault.py`](../scripts/validate-vault.py) (CI-blocking) +
> [`scripts/dedup-vault-sections.py`](../scripts/dedup-vault-sections.py) (remediation).

---

## 1. The question

> *"I don't trust the current md format design structures because I think it's coming
> out of Obsidian vault scope. Analyze the vault docs and search the internet / GitHub
> for the best vault format for a knowledge base of business + DB."*

Two sub-questions:

1. **Is the current format an Obsidian artifact?** Partly — it's *Obsidian-flavored*
   (YAML frontmatter + per-entity markdown files), but it is **not** a real Obsidian
   vault (no `.obsidian/`, no wikilinks graph, no plugins) and Obsidian is **not** in the
   runtime path. So the "Obsidian scope" worry is half-right: we inherited the *shape*
   without any of the tooling that keeps an Obsidian vault consistent.
2. **What format do best-in-class NL→SQL knowledge bases use?** A **semantic layer**:
   structured, machine-checked metadata about tables, columns, relationships, metrics,
   and—most valuable—**verified question→SQL pairs**.

---

## 2. What the vault actually is today

```
docs/vaults/<workspace>/
  glossary.md
  tables/
    FCT_PREP_RECHARGE.md      ← one markdown file per table
    ...
```

Each table file:

- **YAML frontmatter** (machine-read authority): `table`, `database`, `workspace`,
  `keywords[]`, `description`, `generated_at`/`enriched_at` (ISO-8601).
- **Markdown body** (mix of machine- and human-read): `## Columns` (the source-of-truth
  table), `## Column Descriptions`, `## Relationships`, `## Domain Mapping`,
  `## Business Metadata`, `## Example Queries` (`### Q:` + ```sql), `## Sampled Values`.

**Runtime path (this is what matters):** the RAG pipeline reads the **frontmatter**
(`vault_md.py::parse_vault_file`) and selected body sections, embeds them
(`vault_retrieval.py::index_workspace_vault` → Qdrant), retrieves top-N tables for a
question, and injects their reference context into the SQL-generation prompt
(`llm_sql.py::_build_reference_context`). **Obsidian never runs.** The vault is a
plain markdown corpus that happens to use Obsidian conventions.

### 2.1 The real problem: drift, not format

A scan on 2026-06-28 (now encoded as the validator's ERROR set) found:

| Drift | Example | Cause |
|---|---|---|
| **Duplicate sections** | `medianova/all_raw.md` had `## Column Descriptions` ×3, `## Relationships` ×2; `DIM_PREP_PRODUCTS` historically had 12 relationship blocks | legacy enrichment *appended* a new section every pass instead of replacing |
| **Stale placeholder** | every `stc-kuwait` file had `**Description:** No description provided yet.` in the body while frontmatter had a real description | body line mirrored frontmatter once at generation, then never re-synced |
| **Empty metadata** | `FCT_PREP_MASTER_HIST` had 100 columns with blank descriptions, empty `keywords` | never enriched |

Only the first two corrupt the contract (they confuse the LLM and bloat the prompt).
The third is a *gap*, not *corruption* — so the validator treats duplicates/placeholders
as **ERRORS** (block) and empty metadata as **WARN** (signal for enrichment).

> **Conclusion:** markdown is not the problem. The absence of a *schema contract* is.
> An Obsidian vault stays consistent because Obsidian + its plugins enforce structure.
> Our vault had no such enforcement, so every enrichment pass could (and did) drift it.

---

## 3. Industry survey — how NL→SQL knowledge bases are built

Researched the open-source semantic-layer / text-to-SQL ecosystem (GitHub + vendor docs):

| Project | Substrate | Information architecture | Killer artifact |
|---|---|---|---|
| **WrenAI MDL** (Canner) | YAML/JSON ("Modeling Definition Language") | `models/` (columns + expressions), `relationships.yml`, `knowledge/{rules,glossary,metrics,caveats,sql}/` | curated **rules + caveats + sql** knowledge dir |
| **dbt MetricFlow** | YAML | semantic models: `entities` / `dimensions` / `measures`; metrics defined on top | typed **measures/metrics** (no ambiguous aggregation) |
| **Cube** | JS/YAML schema | cubes: `measures`, `dimensions`, `joins`, `segments` | declarative **joins** + pre-agg |
| **Vanna.AI** | vector store | DDL + documentation strings + **question/SQL pairs** | retrieval over **verified Q→SQL pairs** |
| **NotebookLM** (the bar STC set) | source corpus | none (RAG over whole corpus) | full-context grounding + inline citations |

### Two findings that drive our design

1. **Meaning-written-down ≫ format.** Every system that beats keyword matching does so by
   capturing *intent*: which table means what, which column to pick when names mislead
   (`CYCLELENGTH` not `CYCLETYPE`; `FCT_PREP_RECHARGE` not the `REV`-named billing table),
   and **canonical query shapes**. Our `## Domain Mapping` and `## Example Queries`
   sections are exactly this — they're the highest-leverage content, and they were the
   last thing added, not the first.
2. **Verified question→SQL pairs are the single highest-value artifact** (Vanna's whole
   thesis; WrenAI's `knowledge/sql/`). A correct few-shot for "recharge MoM buckets"
   does more for answer quality than perfecting 100 column descriptions. This is why
   `## Example Queries` now carries `question + answer + sql`, and why the validator
   *requires* a ```sql fence in every `### Q:`.

---

## 4. Recommendation — MDL information architecture on a markdown substrate

We do **not** migrate to WrenAI/dbt/Cube. Reasons:

- **Markdown is the right substrate here:** human-editable in the admin UI, git-diffable,
  reviewable in PRs, and directly embeddable for RAG. A YAML/JSON DSL would add a
  compiler + a UI rewrite for zero retrieval benefit.
- **We already have the governance moat** (RLS/CLS/SQL-visibility) the BI semantic layers
  lack. The deficit is metadata *quality*, not the modeling language.

So: **keep the file-per-table markdown, adopt the semantic layer's *discipline*.**

### 4.1 The schema contract (canonical structure)

Each `tables/*.md`:

```markdown
---
table: FCT_PREP_RECHARGE          # required
database: oracle                  # required
workspace: stc-kuwait             # required
keywords: [recharge, topup, ...]  # recommended (WARN if empty)
description: One-line meaning.     # SINGLE SOURCE OF TRUTH (WARN until enriched)
generated_at: '...'               # ISO-8601
enriched_at: '...'
---

# FCT_PREP_RECHARGE

## Columns            ← source of truth for column set (required, non-empty table)
## Column Descriptions  (<=1)
## Relationships        (<=1 — conformed join keys; merged, de-duplicated)
## Domain Mapping       (<=1 — "pick this table when the user says…")
## Business Metadata    (<=1)
## Example Queries      (<=1 — each ### Q: MUST have a ```sql block)
## Sampled Values       (<=1 — live DISTINCT enum literals)
```

**Invariants the contract enforces:**

1. **Frontmatter `description` is the only authority for the table's meaning.** No
   mirrored body placeholder (it only ever drifts). → ERROR on
   `**Description:** No description provided yet.` when frontmatter has a description.
2. **Each canonical section appears at most once.** → ERROR on duplicates.
3. **`## Columns` exists and is non-empty.** → ERROR otherwise.
4. **Every example query has runnable SQL.** → ERROR on a `### Q:` with no ```sql.
5. **No empty relationship bullets** (`` `` → `.` ``). → ERROR.
6. Soft signals (WARN, non-blocking): **missing/empty `description`** (table synced
   but not yet enriched — the sync→enrich lifecycle creates skeletons first), empty
   `keywords`, blank column descriptions, redundant `## Keywords` body section.

Note the asymmetry: a *corrupt* description (present in frontmatter but contradicted
by a stale body placeholder) is an **ERROR**, while a *missing* description is a
**WARN**. Corruption silently degrades answers; absence is a visible, expected step
in the lifecycle that the enrichment workflow then fills.

### 4.2 Enforcement (this is what makes the contract real)

| Tool | Role | When |
|---|---|---|
| [`scripts/validate-vault.py`](../scripts/validate-vault.py) | **the contract** — pure-stdlib checker, exits non-zero on any ERROR | CI job `vault-validate` (BLOCKING, in `.github/workflows/ci.yml`); locally any time |
| [`scripts/dedup-vault-sections.py`](../scripts/dedup-vault-sections.py) | **remediation** — collapses duplicate sections, merges relationships, strips the stale placeholder; idempotent | run when the validator flags drift: `python3 scripts/dedup-vault-sections.py <workspace>` |

CI now fails the build if any vault file drifts out of contract, so the duplicated /
stale-section regression **cannot silently return**. Run `--strict` locally to also surface
the WARN-level metadata gaps as a TODO list for enrichment.

### 4.3 The writers conform (drift can't re-enter at the source)

The validator is reactive; the *writers* are where drift is born. All three write
paths now emit the contract structure, so a fresh sync/enrich can't re-introduce what
the validator just cleaned:

| Writer | Path | Fix |
|---|---|---|
| `vault_sync._generate_new_markdown` | sync discovers a new table | dropped the stale `**Description:**` placeholder + the empty `## Keywords` body |
| `vault_generator.generate_table_markdown` | API schema discovery | description now written to **frontmatter** (was body-only → not retrievable); dropped the duplicate body line + `## Keywords` body |
| `enrich_vault_table` | auto-fill / import-metadata | strips any legacy body placeholder after setting frontmatter `description` |

Covered by `backend/tests/test_vault_enrich_routing.py` — each writer's output is run
through `validate-vault.py`'s own checker and asserted error-free.

### 4.4 What's intentionally still WARN, not ERROR

Empty column descriptions and empty keywords are *completeness* gaps, addressed by the
Sprint-C LLM backfill (draft→review→apply) and live enum sampling — not structural
corruption. Promoting them to ERROR would block CI on every freshly-synced table before a
human can curate it. They stay visible (every run prints them; `--strict` fails on them)
without gating the pipeline.

---

## 5. Sources

- WrenAI / MDL — github.com/Canner/WrenAI (`wren-core`, MDL spec, `knowledge/` dir)
- dbt Semantic Layer / MetricFlow — docs.getdbt.com (semantic models: entities/dimensions/measures)
- Cube — cube.dev/docs (data modeling: measures/dimensions/joins/segments)
- Vanna.AI — github.com/vanna-ai/vanna (RAG over DDL + docs + question/SQL pairs)
- NotebookLM — the customer-set quality bar (full-corpus grounding + citations)

---

## 6. Related

- [`docs/technical-architecture.md`](technical-architecture.md) — overall system authority
- [`docs/pipeline-flow.md`](pipeline-flow.md) — NL→SQL pipeline detail
- Sprint plan: vault enrichment & retrieval (Sprints A–E) — the metadata-quality program
  this contract underpins
