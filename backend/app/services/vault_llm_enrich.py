"""LLM-assisted backfill of empty vault metadata.

Generates DRAFT enrichment (table description, keywords, per-column
descriptions, FK relationships) for tables whose metadata is empty, in the
customer's language. Drafts are returned for human review — nothing is written
here (a wrong column description silently degrades every future query, so an
admin must approve before it influences SQL generation).

Pairs with:
- generate_table_enrichment()  -> TableEnrichmentDraft   (read-only, LLM call)
- draft_to_enrichment()        -> TableEnrichment         (for the apply step)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.schema_discovery.enrichment import (
    ColumnEnrichment,
    RelationshipEnrichment,
    TableEnrichment,
)
from backend.app.services.llm_resolver import ResolvedLLM
from backend.app.services.vault_md import parse_vault_file, read_enum_block, resolve_vault_file
from backend.app.services.workspace_language import get_workspace_language, language_directive

logger = logging.getLogger(__name__)

VALID_FIELDS = {"description", "keywords", "columns", "relationships"}


class ColumnDraft(BaseModel):
    name: str
    current_description: str | None = None
    suggested_description: str | None = None
    is_empty: bool = True


class RelationshipDraft(BaseModel):
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "foreign_key"
    description: str | None = None
    confidence: float = 0.5


class TableEnrichmentDraft(BaseModel):
    table_name: str
    current_description: str | None = None
    suggested_description: str | None = None
    current_keywords: list[str] = Field(default_factory=list)
    suggested_keywords: list[str] = Field(default_factory=list)
    columns: list[ColumnDraft] = Field(default_factory=list)
    relationships: list[RelationshipDraft] = Field(default_factory=list)
    language: str = "en"
    status: str = "ok"  # ok | skipped | error
    error: str | None = None


_KEY_HINTS = ("CONTRNO", "SUBNO", "MSISDN")


def _heuristic_relationships(
    table_name: str, columns: list[dict], neighbor_tables: list[str]
) -> list[dict]:
    """Cheap FK candidates: shared key-ish columns that name a neighbor table.

    Returns dicts {source_column, target_table, confidence} for the LLM to
    confirm/describe. Pure heuristic — never authoritative.
    """
    out: list[dict] = []
    neighbors_lower = {n.lower(): n for n in neighbor_tables if n.lower() != table_name.lower()}
    for c in columns:
        name = c["name"].upper()
        is_keyish = name in _KEY_HINTS or name.endswith("_ID") or name.endswith("NO")
        if not is_keyish:
            continue
        # match a neighbor whose name contains the key token (e.g. SUBNO -> DIM_SUBSCRIBER)
        for low, original in neighbors_lower.items():
            token = name.replace("_ID", "").replace("NO", "").lower()
            if token and len(token) >= 3 and token in low:
                out.append(
                    {"source_column": c["name"], "target_table": original, "confidence": 0.5}
                )
                break
    return out


def _build_prompt(
    table_name: str,
    parsed: dict,
    enum_values: dict[str, list[str]],
    want: set[str],
    neighbor_tables: list[str],
    heuristics: list[dict],
    lang_directive: str,
) -> str:
    col_lines = []
    for c in parsed["columns"]:
        line = f"  - {c['name']} ({c['type']})"
        ev = enum_values.get(c["name"])
        if ev:
            line += f"  sample values: {', '.join(ev[:15])}"
        col_lines.append(line)
    cols_block = "\n".join(col_lines)

    contract: dict = {}
    if "description" in want:
        contract["table_description"] = "string (1-2 sentences, business meaning)"
    if "keywords" in want:
        contract["keywords"] = ["string (5-12 short search terms incl. synonyms)"]
    if "columns" in want:
        contract["columns"] = [{"name": "EXACT_COLUMN_NAME", "description": "string"}]
    if "relationships" in want:
        contract["relationships"] = [
            {
                "source_column": "EXACT_COLUMN_NAME",
                "target_table": "EXACT_NEIGHBOR_TABLE",
                "target_column": "string",
                "relationship_type": "foreign_key",
                "description": "string",
                "confidence": 0.0,
            }
        ]

    parts = [
        "You are a data catalog expert documenting an enterprise database table.",
        lang_directive,
        "",
        "IMPORTANT: descriptions and keywords MUST be in the language above, but "
        "table names and column names are identifiers — keep them VERBATIM.",
        "Only use column names from the provided list. Only point relationships at "
        "one of the provided neighbor tables. If unsure, omit rather than guess.",
        "",
        f"Table: {table_name}",
        "Columns:",
        cols_block,
    ]
    if "relationships" in want:
        parts += [
            "",
            f"Candidate neighbor tables (for FK targets): {', '.join(neighbor_tables[:40])}",
        ]
        if heuristics:
            parts += [
                "Heuristic FK candidates to confirm or reject:",
                json.dumps(heuristics),
            ]
    parts += [
        "",
        "Return ONLY a valid JSON object with EXACTLY this shape "
        "(omit a key if you have no high-confidence value):",
        json.dumps(contract, indent=2),
    ]
    return "\n".join(parts)


async def generate_table_enrichment(
    workspace_id: str,
    table_name: str,
    mode: str = "fill_empty",
    fields: list[str] | None = None,
    llm: ResolvedLLM | None = None,
    neighbor_tables: list[str] | None = None,
) -> TableEnrichmentDraft:
    """Produce a review draft of LLM-suggested metadata for one table.

    mode="fill_empty" only asks for fields that are currently blank;
    mode="overwrite" asks for all requested fields regardless. Never writes.
    """
    import litellm

    settings = get_settings()
    want = set(fields) & VALID_FIELDS if fields else set(VALID_FIELDS)
    neighbor_tables = neighbor_tables or []

    vault_dir = Path(settings.vault_base_path) / workspace_id / "tables"
    filepath = resolve_vault_file(vault_dir, table_name)
    if not filepath.exists():
        return TableEnrichmentDraft(
            table_name=table_name, status="error", error=f"Vault file not found: {filepath.name}"
        )

    parsed = parse_vault_file(filepath)
    enum_values = read_enum_block(filepath)
    language = await get_workspace_language(workspace_id)

    desc_empty = not (parsed.get("description") or "").strip()
    kw_empty = len(parsed.get("keywords") or []) == 0
    rels_empty = len(parsed.get("relationships") or []) == 0
    empty_cols = {c["name"] for c in parsed["columns"] if not (c.get("description") or "").strip()}

    # Decide what to actually ask for.
    ask = set()
    if "description" in want and (mode == "overwrite" or desc_empty):
        ask.add("description")
    if "keywords" in want and (mode == "overwrite" or kw_empty):
        ask.add("keywords")
    if "columns" in want and (mode == "overwrite" or empty_cols):
        ask.add("columns")
    if "relationships" in want and (mode == "overwrite" or rels_empty):
        ask.add("relationships")

    draft = TableEnrichmentDraft(
        table_name=parsed.get("table_name") or table_name,
        current_description=parsed.get("description"),
        current_keywords=parsed.get("keywords") or [],
        language=language,
    )
    if not ask:
        draft.status = "skipped"
        return draft

    heuristics = (
        _heuristic_relationships(table_name, parsed["columns"], neighbor_tables)
        if "relationships" in ask
        else []
    )
    prompt = _build_prompt(
        table_name,
        parsed,
        enum_values,
        ask,
        neighbor_tables,
        heuristics,
        language_directive(language),
    )

    # Mirror llm_insight.py: a resolved LLM with an EMPTY api_key (e.g. a workspace
    # BYOK config with no virtual key) must still fall back to the platform key.
    # Passing "" to litellm with custom_llm_provider="openai" fails client-side with
    # "OpenAIException - Missing credentials" — which is what broke the auto-fill button.
    model = (llm.model if llm and llm.model else None) or settings.llm_model
    api_base = (llm.api_base if llm and llm.api_base else None) or settings.litellm_api_base
    api_key = (
        (llm.api_key if llm and llm.api_key else None)
        or settings.litellm_api_key
        or "sk-placeholder"
    )

    try:
        resp = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=60.0,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="openai",
        )
        result = json.loads(resp.choices[0].message.content)
    except Exception as e:  # noqa: BLE001 — graceful degrade, never raise
        logger.warning("LLM enrichment failed for %s: %s", table_name, e)
        draft.status = "error"
        draft.error = str(e)
        return draft

    # ── validate + map into the draft, filtering hallucinations ──
    valid_cols = {c["name"].lower(): c["name"] for c in parsed["columns"]}
    valid_neighbors = {n.lower() for n in neighbor_tables}

    if "description" in ask and isinstance(result.get("table_description"), str):
        draft.suggested_description = result["table_description"].strip() or None

    if "keywords" in ask and isinstance(result.get("keywords"), list):
        draft.suggested_keywords = [str(k).strip() for k in result["keywords"] if str(k).strip()]

    if "columns" in ask and isinstance(result.get("columns"), list):
        for c in result["columns"]:
            if not isinstance(c, dict):
                continue
            cname = str(c.get("name", "")).strip()
            key = cname.lower()
            if key not in valid_cols:
                continue  # hallucinated column — drop
            real = valid_cols[key]
            # in fill_empty, only surface columns whose current desc is blank
            if mode == "fill_empty" and real not in empty_cols:
                continue
            draft.columns.append(
                ColumnDraft(
                    name=real,
                    current_description=next(
                        (
                            col.get("description")
                            for col in parsed["columns"]
                            if col["name"] == real
                        ),
                        None,
                    ),
                    suggested_description=str(c.get("description", "")).strip() or None,
                    is_empty=real in empty_cols,
                )
            )

    if "relationships" in ask and isinstance(result.get("relationships"), list):
        for r in result["relationships"]:
            if not isinstance(r, dict):
                continue
            src = str(r.get("source_column", "")).strip()
            tgt_table = str(r.get("target_table", "")).strip()
            if src.lower() not in valid_cols:
                continue  # source must be a real column
            if valid_neighbors and tgt_table.lower() not in valid_neighbors:
                continue  # target must be a known table
            try:
                conf = float(r.get("confidence", 0.6))
            except (TypeError, ValueError):
                conf = 0.6
            draft.relationships.append(
                RelationshipDraft(
                    source_column=valid_cols[src.lower()],
                    target_table=tgt_table,
                    target_column=str(r.get("target_column", "")).strip() or src,
                    relationship_type=str(r.get("relationship_type", "foreign_key")),
                    description=str(r.get("description", "")).strip() or None,
                    confidence=conf,
                )
            )

    return draft


def draft_to_enrichment(
    draft: TableEnrichmentDraft, mode: str, fields: list[str] | None = None
) -> TableEnrichment:
    """Convert a (possibly human-edited) draft into a TableEnrichment for apply.

    In fill_empty mode, populated fields are dropped so enrich_vault_table (which
    OVERWRITES description and UNIONs keywords) never clobbers existing content.
    """
    want = set(fields) & VALID_FIELDS if fields else set(VALID_FIELDS)

    description = None
    if (
        "description" in want
        and draft.suggested_description
        and (mode == "overwrite" or not (draft.current_description or "").strip())
    ):
        description = draft.suggested_description

    keywords = None
    if "keywords" in want and draft.suggested_keywords:
        keywords = draft.suggested_keywords

    columns: list[ColumnEnrichment] = []
    if "columns" in want:
        for c in draft.columns:
            if not c.suggested_description:
                continue
            if mode == "fill_empty" and not c.is_empty:
                continue
            columns.append(ColumnEnrichment(name=c.name, description=c.suggested_description))

    relationships: list[RelationshipEnrichment] = []
    if "relationships" in want:
        for r in draft.relationships:
            relationships.append(
                RelationshipEnrichment(
                    source_column=r.source_column,
                    target_table=r.target_table,
                    target_column=r.target_column,
                    relationship_type=r.relationship_type,
                    description=r.description,
                )
            )

    return TableEnrichment(
        table_name=draft.table_name,
        description=description,
        keywords=keywords,
        columns=columns,
        relationships=relationships,
    )
