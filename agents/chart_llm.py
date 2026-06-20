"""LLM-based chart proposer.

Translates a natural-language question + data preview into a
structured ``ChartConfig``, selecting the best chart type and
axis mappings.

Architecture:
  1. ``LlmChartChoice`` — Pydantic BaseModel for the structured output
     (chart_type, x_column, y_column, title, labels, reasoning).
  2. ``_run_chart_llm()`` — calls the LiteLLM proxy in JSON mode and
     validates the response into an ``LlmChartChoice``.
  3. ``propose_chart_llm()`` — async wrapper: build the prompt, run the
     LLM, return a ``ChartConfig``.
  4. ``propose_chart_llm_with_heuristic()`` — hybrid: LLM takes the
     heuristic suggestion as a prior and may override.

The LLM call goes through the same LiteLLM proxy as the rest of the
backend (``llm_insight``/``llm_sql``); we ask for a JSON object and
validate it with Pydantic rather than pulling in a separate agent
framework.
"""

from __future__ import annotations

import json

import litellm
import structlog
from pydantic import BaseModel, Field

from agents.chart_heuristic import (
    _cardinality,
    _classify_columns,
    _extract_values,
)
from agents.chart_types import AxisConfig, ChartConfig, ChartType

log = structlog.get_logger(__name__)


# ── Structured output ──────────────────────────────────────────────────────


class LlmChartChoice(BaseModel):
    """Structured output from the LLM chart proposer.

    The LLM is asked to pick the ONE best chart type and configure
    axes, labels, and title.
    """

    chart_type: str = Field(
        default="table",
        description="One of: bar, line, scatter, pie, area, table.",
    )

    x_column: str = Field(
        default="",
        description="Column name for the X axis (or category for pie).",
    )

    y_column: str = Field(
        default="",
        description="Column name for the Y axis (or value for pie).",
    )

    color_column: str = Field(
        default="",
        description="Optional column for colour grouping.",
    )

    title: str = Field(
        default="",
        description="Short, human-readable chart title.",
    )

    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Column name → human-readable display label mapping.",
    )

    reasoning: str = Field(
        default="",
        description="Why this chart type was chosen, in one sentence.",
    )

    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this choice (0=guess, 1=certain).",
    )


# ── Data preview ───────────────────────────────────────────────────────────


def _build_data_preview(
    rows: list[dict],
    columns: list[str],
    max_preview_rows: int = 5,
) -> str:
    """Build a compact data preview for the LLM prompt.

    Includes column metadata (name, type, cardinality, sample values)
    and first N rows.
    """
    if not rows:
        return "(empty dataset)"

    classified = _classify_columns(rows, columns)

    # Column metadata table
    lines = ["## Column Metadata\n"]
    lines.append("| # | Column | Type | Cardinality | Sample Values |")
    lines.append("|---|--------|------|-------------|---------------|")

    for i, col in enumerate(columns, 1):
        values = _extract_values(rows, col)
        card = _cardinality(values)
        non_null = [v for v in values if v is not None]

        if col in classified["numeric"]:
            dtype = "numeric"
            samples = ", ".join(str(v) for v in non_null[:3] if isinstance(v, (int, float)))
        elif col in classified["datetime"]:
            dtype = "datetime"
            samples = ", ".join(str(v)[:19] for v in non_null[:3])
        else:
            dtype = "categorical"
            samples = ", ".join(str(v) for v in non_null[:3])

        lines.append(f"| {i} | {col} | {dtype} | {card} | {samples[:60]} |")

    # First N rows
    lines.append(f"\n## Data Preview (first {min(max_preview_rows, len(rows))} rows)\n")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")

    for row in rows[:max_preview_rows]:
        vals = [str(row.get(c, ""))[:40] for c in columns]
        lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines)


# ── System prompt ──────────────────────────────────────────────────────────


_SYSTEM_PROMPT = """\
You are a data visualisation expert.  Given a dataset preview and a user
question, pick the SINGLE best chart type and configure axes.

## Available chart types
- **bar**: Compare categories.  1 categorical + 1 numeric.  Use when there
  are ≤30 categories.  Horizontal for >10 categories.
- **line**: Show trends over time.  1 datetime + 1+ numeric columns.
- **scatter**: Show relationship between two numeric variables.
- **pie**: Show proportions of a whole.  1 categorical (2-8 values) + 1 numeric.
- **area**: Show cumulative or volume trends.  Like line but with filled area.
- **table**: Fallback when data doesn't suit any chart type.

## Rules
- ALWAYS pick exactly one chart type.
- Map the most meaningful columns to x and y axes.
- For pie charts: x = category column, y = value column.
- For tables: leave x/y empty.
- Title should be short (≤60 chars) and descriptive.
- Labels map column names to human-friendly names.
- Confidence should reflect how certain you are: 0.9+ for obvious matches,
  0.5-0.7 for ambiguous data.

Respond ONLY with the structured output — no extra text.
"""


# ── User prompt ────────────────────────────────────────────────────────────


def _build_user_prompt(
    question: str,
    data_preview: str,
    heuristic_hint: ChartConfig | None = None,
) -> str:
    """Build the user prompt with data preview and optional heuristic hint."""
    parts = []

    if question:
        parts.append(f"## User Question\n{question}\n")

    parts.append(data_preview)

    if heuristic_hint and heuristic_hint.chart_type != ChartType.TABLE:
        parts.append(
            "\n## Heuristic Suggestion (consider but override if wrong)\n"
            f"Heuristic recommended: **{heuristic_hint.chart_type.value}**\n"
            f"Reason: {heuristic_hint.reasoning}\n"
            f"Suggested X: {heuristic_hint.x.column}, Y: {heuristic_hint.y.column}\n"
        )

    parts.append("\nPick the best chart type. Respond with structured output only.")

    return "\n".join(parts)


# ── Model resolution ───────────────────────────────────────────────────────


def _resolve_model(model_name: str | None = None) -> str:
    """Resolve LLM model name — defaults to 'chart' role model.

    In production this would call ``backend.app.llm.get_model(\"chart\")``.
    """
    if model_name:
        return model_name
    return "gpt-4o"


# ── LLM call ─────────────────────────────────────────────────────────────


async def _run_chart_llm(
    prompt: str,
    *,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
) -> LlmChartChoice:
    """Call the LiteLLM proxy in JSON mode and validate the chart choice.

    Returns a default (table) ``LlmChartChoice`` if the call or the
    validation fails, so chart proposal degrades gracefully instead of
    raising.
    """
    try:
        response = await litellm.acompletion(
            model=_resolve_model(model_name),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=30.0,
            api_base=llm_base_url,
            api_key=llm_api_key or "sk-dummy",
            custom_llm_provider="openai",
        )
        content = response.choices[0].message.content
        return LlmChartChoice.model_validate(json.loads(content))
    except Exception as exc:  # noqa: BLE001 — degrade to table on any LLM/parse error
        log.warning("chart_llm.failed", error=str(exc))
        return LlmChartChoice(
            chart_type="table",
            confidence=0.0,
            reasoning="LLM call failed — table fallback.",
        )


# ── Public API ─────────────────────────────────────────────────────────────


async def propose_chart_llm(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    heuristic_hint: ChartConfig | None = None,
    max_preview_rows: int = 5,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
) -> ChartConfig:
    """Use an LLM to propose the best chart type and configuration.

    Args:
        rows: Query result rows (list of dicts).
        columns: Ordered column names (inferred from first row if None).
        question: Original NL question for context.
        heuristic_hint: Optional heuristic result the LLM can use as prior.
        max_preview_rows: How many data rows to include in the preview.
        model_name: Override LLM model.
        llm_base_url: API endpoint.
        llm_api_key: API key.

    Returns:
        ChartConfig with LLM-chosen chart type, axes, labels, title.
    """
    if not rows:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            reasoning="No data rows — table fallback.",
            confidence=0.0,
        )

    if columns is None:
        columns = list(rows[0].keys())

    data_preview = _build_data_preview(rows, columns, max_preview_rows)
    prompt = _build_user_prompt(question, data_preview, heuristic_hint)

    log.info(
        "chart_llm.start",
        rows=len(rows),
        cols=len(columns),
        question_chars=len(question),
        has_heuristic_hint=heuristic_hint is not None,
        model=_resolve_model(model_name),
    )

    choice = await _run_chart_llm(
        prompt,
        model_name=model_name,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
    )

    # Map LLM output → ChartConfig
    try:
        chart_type = ChartType(choice.chart_type.lower())
    except ValueError:
        log.warning(
            "chart_llm.invalid_type",
            raw_type=choice.chart_type,
            fallback="table",
        )
        chart_type = ChartType.TABLE

    config = ChartConfig(
        chart_type=chart_type,
        title=choice.title,
        x=AxisConfig(column=choice.x_column, label=choice.x_column),
        y=AxisConfig(column=choice.y_column, label=choice.y_column),
        color_column=choice.color_column,
        labels=choice.labels,
        confidence=choice.confidence,
        reasoning=choice.reasoning,
    )

    log.info(
        "chart_llm.chosen",
        chart_type=config.chart_type.value,
        x=config.x.column,
        y=config.y.column,
        confidence=config.confidence,
    )

    return config


async def propose_chart_llm_with_heuristic(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
) -> ChartConfig:
    """Hybrid: run heuristic first, then escalate to LLM with the hint.

    The LLM sees the heuristic suggestion as a prior but can override
    it if the data preview suggests a better chart type.

    Returns the LLM result directly (which may confirm or override
    the heuristic).
    """
    from agents.chart_heuristic import propose_chart

    if columns is None:
        columns = list(rows[0].keys()) if rows else []

    heuristic_hint = propose_chart(rows, columns=columns, question=question)

    return await propose_chart_llm(
        rows,
        columns=columns,
        question=question,
        heuristic_hint=heuristic_hint,
        model_name=model_name,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
    )
