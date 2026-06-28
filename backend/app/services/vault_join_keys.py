"""Conformed join-key management for a workspace's vault.

This schema (STC prepaid) has NO enforced foreign keys and no owning dimension
for the shared identifiers — SUBNO (line/MSISDN) and CONTRNO (contract/customer)
recur across many fact tables and any two tables sharing such a key can be
joined on it. So a relationship here is a property of a *shared key*, not of a
table pair.

This module:
- derive_candidates(): scans every vault table's column list and surfaces
  columns present in >= 2 tables (the conformed-key candidates).
- load/save curation: the admin marks which candidates are real join keys,
  their grain (line/customer/other) and a note — persisted to
  ``<vault>/<workspace>/join_keys.json``.
- get_join_keys(): live candidates merged with saved curation (so new shared
  columns appear unconfirmed and removed columns drop off).
- build_join_keys_context(): renders the CONFIRMED keys as guidance injected
  into the SQL-generation prompt for every multi-table question.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.services.vault_md import parse_vault_file

logger = logging.getLogger(__name__)

# Grain is FREE TEXT, inferred by the LLM during vault processing (see
# infer_grains). No hardcoded grain map — the model decides from the column's
# vault description + the tables it appears in.
_MIN_TABLES = 2  # a column must appear in >= this many tables to be a candidate


def _tables_dir(workspace_id: str) -> Path:
    return Path(get_settings().vault_base_path) / workspace_id / "tables"


def _curation_path(workspace_id: str) -> Path:
    return Path(get_settings().vault_base_path) / workspace_id / "join_keys.json"


def _scan(workspace_id: str) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Single vault scan → (col → member tables, col → a representative description)."""
    tables_dir = _tables_dir(workspace_id)
    col_to_tables: dict[str, set[str]] = {}
    col_to_desc: dict[str, str] = {}
    if not tables_dir.exists():
        return col_to_tables, col_to_desc
    for md in sorted(tables_dir.glob("*.md")):
        parsed = parse_vault_file(md)
        tname = parsed.get("table_name") or md.stem
        for c in parsed.get("columns", []):
            name = (c.get("name") or "").strip().upper()
            if not name:
                continue
            col_to_tables.setdefault(name, set()).add(tname)
            desc = (c.get("description") or "").strip()
            if desc and not col_to_desc.get(name):
                col_to_desc[name] = desc
    return col_to_tables, col_to_desc


def derive_candidates(workspace_id: str) -> dict[str, list[str]]:
    """Return {COLUMN: [member_table, ...]} for columns shared by >= _MIN_TABLES tables."""
    col_to_tables, _ = _scan(workspace_id)
    return {col: sorted(tbls) for col, tbls in col_to_tables.items() if len(tbls) >= _MIN_TABLES}


def load_curation(workspace_id: str) -> dict[str, dict[str, Any]]:
    """Saved per-column decisions keyed by UPPER column name."""
    p = _curation_path(workspace_id)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {k.upper(): v for k, v in data.get("keys", {}).items()}
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to read join_keys.json for %s: %s", workspace_id, e)
        return {}


def save_curation(workspace_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist curation. items: [{column, is_join_key, grain, note}]."""
    keys: dict[str, dict[str, Any]] = {}
    for it in items:
        col = (it.get("column") or "").strip().upper()
        if not col:
            continue
        keys[col] = {
            "is_join_key": bool(it.get("is_join_key", False)),
            "grain": (it.get("grain") or "").strip() or None,
            "note": (it.get("note") or "").strip() or None,
        }
    p = _curation_path(workspace_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"keys": keys}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": len(keys)}


def get_join_keys(workspace_id: str) -> list[dict[str, Any]]:
    """Live candidates merged with saved curation, sorted by member-table count."""
    candidates = derive_candidates(workspace_id)
    curation = load_curation(workspace_id)
    out: list[dict[str, Any]] = []
    for col, tables in candidates.items():
        cur = curation.get(col, {})
        out.append(
            {
                "column": col,
                "member_tables": tables,
                "occurrences": len(tables),
                "is_join_key": cur.get("is_join_key", False),
                "grain": cur.get("grain"),
                "note": cur.get("note"),
            }
        )
    out.sort(key=lambda r: (not r["is_join_key"], -r["occurrences"], r["column"]))
    return out


async def infer_grains(workspace_id: str, llm=None, overwrite: bool = False) -> dict[str, Any]:
    """LLM-infer a SHORT free-text grain for each shared-column candidate, using
    the column's vault description + the tables it appears in. One batched call.

    Only fills columns whose grain is currently empty (unless ``overwrite``),
    so manual edits are preserved. Persists into join_keys.json. Returns
    {filled, total, model}.
    """
    import json

    import litellm

    col_to_tables, col_to_desc = _scan(workspace_id)
    candidates = {c: sorted(t) for c, t in col_to_tables.items() if len(t) >= _MIN_TABLES}
    if not candidates:
        return {"filled": 0, "total": 0}

    curation = load_curation(workspace_id)
    targets = [
        c for c in candidates if overwrite or not (curation.get(c, {}).get("grain") or "").strip()
    ]
    if not targets:
        return {"filled": 0, "total": len(candidates)}

    payload = [
        {
            "column": c,
            "description": col_to_desc.get(c, ""),
            "tables": candidates[c][:8],
        }
        for c in targets[:200]
    ]
    prompt = (
        "You are a data modeler for a telco prepaid database that has NO enforced "
        "foreign keys. Each column below is shared across multiple tables and may be "
        "used as a JOIN key. For EACH, return a SHORT free-text 'grain' label "
        "describing what ONE value of the column identifies — e.g. 'line (MSISDN)', "
        "'customer / contract', 'product / plan', 'calendar date', 'recharge "
        "transaction', 'cell / network element'. 2-4 words max. If the column is a "
        "descriptive attribute rather than an identifier (e.g. a status or region "
        "name), return 'attribute (not a join key)'.\n\n"
        'Return ONLY JSON: {"COLUMN": "grain label", ...}.\n\n'
        f"Columns:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    settings = get_settings()
    model = (llm.model if llm and getattr(llm, "model", None) else None) or settings.llm_model
    api_base = (
        llm.api_base if llm and getattr(llm, "api_base", None) else None
    ) or settings.litellm_api_base
    api_key = (
        (llm.api_key if llm and getattr(llm, "api_key", None) else None)
        or settings.litellm_api_key
        or "sk-dummy"
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
    except Exception as e:  # noqa: BLE001
        logger.warning("Grain inference failed: %s", e)
        return {"filled": 0, "total": len(candidates), "error": str(e)}

    filled = 0
    for col in targets:
        grain = result.get(col) or result.get(col.upper()) or result.get(col.lower())
        if isinstance(grain, str) and grain.strip():
            entry = curation.get(col, {})
            entry["grain"] = grain.strip()
            entry.setdefault("is_join_key", False)
            entry.setdefault("note", None)
            curation[col] = entry
            filled += 1

    # persist
    save_curation(
        workspace_id,
        [{"column": c, **v} for c, v in curation.items()],
    )
    return {"filled": filled, "total": len(candidates), "model": model}


def build_join_keys_context(workspace_id: str) -> str:
    """Render CONFIRMED join keys as LLM guidance. Empty string if none confirmed."""
    keys = [k for k in get_join_keys(workspace_id) if k["is_join_key"]]
    if not keys:
        return ""
    lines = [
        "\nCONFORMED JOIN KEYS (this database has NO enforced foreign keys). Any two "
        "tables that share one of these columns can be JOINed on it — there is no single "
        "owning/dimension table. Match the grain to the question:",
    ]
    for k in keys:
        grain = f" [{k['grain']} grain]" if k.get("grain") else ""
        note = f" — {k['note']}" if k.get("note") else ""
        tbls = ", ".join(k["member_tables"][:12])
        lines.append(
            f"- `{k['column']}`{grain}: join on a.{k['column']} = b.{k['column']}. "
            f"Present in: {tbls}.{note}"
        )
    return "\n".join(lines)
