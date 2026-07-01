import json
import logging
import re
from typing import Any

import litellm

from backend.app.core.config import get_settings
from backend.app.services.litellm_meta import litellm_meta
from backend.app.services.llm_resolver import ResolvedLLM
from backend.app.services.workspace_language import language_directive

logger = logging.getLogger(__name__)

# Models name the follow-up array inconsistently; accept the common variants
# instead of silently dropping suggestions that arrived under a different key.
_SUGGESTION_KEYS = ("suggestions", "follow_ups", "followups", "questions")
# When a suggestion arrives as an object, pull the text from the first key present.
_SUGGESTION_TEXT_KEYS = ("question", "text", "q", "value", "suggestion")
# Strip leading list markers ("1. ", "2) ", "- ", "* ", "• ") from string forms.
_LIST_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*")


def _coerce_suggestion(item: Any) -> str | None:
    """Coerce one suggestion item (string or object) to clean text, or None."""
    if isinstance(item, str):
        text = _LIST_MARKER_RE.sub("", item).strip()
        return text or None
    if isinstance(item, dict):
        for key in _SUGGESTION_TEXT_KEYS:
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                return _LIST_MARKER_RE.sub("", val).strip()
    return None


def _normalize_suggestions(result: dict[str, Any]) -> list[str]:
    """Tolerantly extract up to 3 follow-up questions from an LLM JSON object.

    Handles the shapes seen in the wild: a list of strings, a list of objects
    (``[{"question": ...}]``), a newline-delimited string, and the array living
    under an alternate key (``follow_ups``/``questions``). Anything unparseable
    yields ``[]`` (the caller logs that case for diagnosis).
    """
    for key in _SUGGESTION_KEYS:
        raw = result.get(key)
        if not raw:
            continue
        items: list[Any]
        if isinstance(raw, str):
            items = raw.splitlines()
        elif isinstance(raw, list):
            items = raw
        else:
            continue
        cleaned = [s for s in (_coerce_suggestion(i) for i in items) if s]
        if cleaned:
            return cleaned[:3]
    return []


async def generate_insight_and_suggestions(
    question: str,
    sql: str,
    data_rows: list[dict[str, Any]],
    llm: ResolvedLLM | None = None,
    language: str = "en",
    workspace_id: str | None = None,
) -> dict:
    """Generate executive summary and follow-up suggestions from query results.

    Args:
        question: Original user question
        sql: The SQL that was executed
        data_rows: Up to 10 rows of data from the result

    Returns:
        dict: {"summary": "str", "suggestions": ["Q1", "Q2", "Q3"]}
    """
    settings = get_settings()

    prompt = f"""You are an executive data analyst. You are provided with a user's question, the SQL query used to fetch data, and a sample of the results (up to 10 rows).

{language_directive(language)}

Your task is to provide:
1. A brief executive summary (max 2 sentences) interpreting the results.
2. 3 insightful follow-up questions the user might want to ask next to drill down or pivot.

Return ONLY a valid JSON object matching this schema:
{{
  "summary": "Your executive summary here...",
  "suggestions": ["Follow-up question 1", "Follow-up question 2", "Follow-up question 3"]
}}

Question: {question}
SQL: {sql}
Result Sample:
{json.dumps(data_rows, default=str)}
"""

    try:
        # Mirror llm_sql.py's credential derivation: a resolved LLM with an EMPTY
        # api_key must still fall back to the platform key / placeholder. Passing
        # "" to litellm (custom_llm_provider="openai") fails client-side with
        # "Missing credentials", which silently degrades every answer to the
        # generic fallback summary with no suggestions.
        model_name = (llm.model if llm and llm.model else None) or settings.llm_model
        api_base = (llm.api_base if llm and llm.api_base else None) or settings.litellm_api_base
        api_key = (
            (llm.api_key if llm and llm.api_key else None)
            or settings.litellm_api_key
            or "sk-placeholder"
        )

        response = await litellm.acompletion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=30.0,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="openai",
            **litellm_meta("insight", tenant=workspace_id),
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Ensure correct structure. Suggestions arrive in inconsistent shapes
        # (list of strings/objects, newline string, alternate key); normalize
        # tolerantly instead of silently dropping anything that isn't a
        # list[str] — that drop cost real answers their follow-ups with no trace.
        summary = result.get("summary", "Query executed successfully.")
        suggestions = _normalize_suggestions(result if isinstance(result, dict) else {})

        if summary and not suggestions:
            logger.warning(
                "Insight produced a summary but no usable suggestions; raw content: %s",
                (content or "")[:500],
            )

        from backend.app.services.llm_cost import extract_cost, extract_usage

        usage = extract_usage(response)
        # Carry LiteLLM's response_cost forward for metering (Task 13); str() so the value
        # survives the pipeline's dict rebuild uniformly with the httpx-header path.
        _cost = extract_cost(response)
        usage["_response_cost"] = str(_cost) if _cost is not None else None
        return {"summary": summary, "suggestions": suggestions, "usage": usage}
    except Exception as e:
        logger.warning(f"Failed to generate insights: {e}")
        return {"summary": "Data retrieved successfully.", "suggestions": []}
