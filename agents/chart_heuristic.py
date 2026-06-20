"""Zero-LLM heuristic chart proposer.

Analyses query result structure (column types, cardinality, row count,
value distribution) and returns a ``ChartConfig`` with a recommended
chart type — no LLM call required.

Heuristic rules (ordered by priority):
  1. TABLE   — >10 columns or >200 rows → table
  2. PIE     — 1 low-cardinality categorical (<8) + 1 numeric, few rows
  3. LINE    — 1 datetime/date + 1+ numeric columns
  4. SCATTER — 2 numeric columns
  5. BAR     — 1 categorical + 1 numeric (most common)
  6. AREA    — 1 categorical + 1+ numeric, stacked intent
  7. TABLE   — fallback

Mirrors bi-indexer's heuristic→LLM escalation pattern: the heuristic
always returns *something* (even if low confidence), and the caller
can optionally escalate to the LLM proposer for refinement.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import structlog

from agents.chart_types import AxisConfig, ChartConfig, ChartType

log = structlog.get_logger(__name__)

# ── Column type detection ──────────────────────────────────────────────────


def _is_numeric(values: list[Any]) -> bool:
    """Check if a column appears numeric (int/float)."""
    numeric = 0
    for v in values:
        if v is None:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric += 1
        elif isinstance(v, str):
            try:
                float(v)
                numeric += 1
            except (ValueError, TypeError):
                return False
        else:
            return False
    return numeric > 0


def _is_datetime(values: list[Any]) -> bool:
    """Check if a column appears to be date/datetime."""
    dt_count = 0
    for v in values:
        if v is None:
            continue
        if isinstance(v, (datetime, date)):
            dt_count += 1
        elif isinstance(v, str):
            # Try ISO format
            for fmt in (
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y",
                "%m/%d/%Y",
            ):
                try:
                    datetime.strptime(v[:19] if len(v) > 19 else v, fmt)
                    dt_count += 1
                    break
                except (ValueError, IndexError):
                    continue
    return dt_count > 0 and dt_count >= len([v for v in values if v is not None]) * 0.5


def _cardinality(values: list[Any]) -> int:
    """Count unique non-null values."""
    return len({v for v in values if v is not None})


def _extract_values(rows: list[dict], column: str) -> list[Any]:
    """Extract a column's values from a list of dicts."""
    return [row.get(column) for row in rows]


# ── Column classification ──────────────────────────────────────────────────


def _classify_columns(rows: list[dict], columns: list[str]) -> dict[str, list[str]]:
    """Classify columns as numeric, datetime, or categorical.

    Returns dict with keys 'numeric', 'datetime', 'categorical'.
    """
    result: dict[str, list[str]] = {
        "numeric": [],
        "datetime": [],
        "categorical": [],
    }

    for col in columns:
        values = _extract_values(rows, col)
        if _is_numeric(values):
            result["numeric"].append(col)
        elif _is_datetime(values):
            result["datetime"].append(col)
        else:
            result["categorical"].append(col)

    return result


# ── Heuristic engine ───────────────────────────────────────────────────────


def propose_chart(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    max_pie_categories: int = 8,
    max_bar_categories: int = 30,
    table_col_threshold: int = 10,
    table_row_threshold: int = 200,
) -> ChartConfig:
    """Propose a chart type based on structured heuristics — zero LLM.

    Args:
        rows: Query result rows (list of dicts).
        columns: Ordered list of column names.  If None, inferred from the
            first row's keys.
        question: Optional NL question for context (used in reasoning).
        max_pie_categories: Max unique values for pie chart categorical.
        max_bar_categories: Max unique values for bar chart categorical.
        table_col_threshold: If column count exceeds this, use table.
        table_row_threshold: If row count exceeds this, use table.

    Returns:
        ChartConfig with the recommended chart type, axes, and reasoning.
    """
    if not rows:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            reasoning="No data rows — falling back to table view.",
            confidence=0.0,
        )

    if columns is None:
        columns = list(rows[0].keys())

    n_rows = len(rows)
    n_cols = len(columns)

    log.info(
        "chart_heuristic.start",
        rows=n_rows,
        cols=n_cols,
        columns=columns,
    )

    # ── Rule 0: Too many columns or rows → table ───────────────────────
    if n_cols > table_col_threshold:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title=_title_from_question(question),
            reasoning=f"{n_cols} columns > {table_col_threshold} threshold — table is safest.",
            confidence=0.9,
        )

    if n_rows > table_row_threshold:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title=_title_from_question(question),
            reasoning=f"{n_rows} rows > {table_row_threshold} threshold — too many for meaningful chart.",
            confidence=0.8,
        )

    classified = _classify_columns(rows, columns)

    num_cols = classified["numeric"]
    dt_cols = classified["datetime"]
    cat_cols = classified["categorical"]

    log.info(
        "chart_heuristic.classified",
        numeric=num_cols,
        datetime=dt_cols,
        categorical=cat_cols,
    )

    # ── Rule 1: Line chart (time series) ──────────────────────────────
    # Highest priority — datetime always wins over other heuristics.
    if dt_cols and num_cols and n_rows >= 2:
        return ChartConfig(
            chart_type=ChartType.LINE,
            title=_title_from_question(question),
            x=AxisConfig(column=dt_cols[0], label=dt_cols[0]),
            y=AxisConfig(column=num_cols[0], label=num_cols[0]),
            reasoning=(
                f"Line chart: datetime '{dt_cols[0]}' on X, "
                f"numeric '{num_cols[0]}' on Y. "
                f"Time-series detected (≥2 points)."
            ),
            confidence=0.85,
        )

    # ── Rule 2: Scatter plot ──────────────────────────────────────────
    if len(num_cols) >= 2:
        return ChartConfig(
            chart_type=ChartType.SCATTER,
            title=_title_from_question(question),
            x=AxisConfig(column=num_cols[0], label=num_cols[0]),
            y=AxisConfig(column=num_cols[1], label=num_cols[1]),
            reasoning=(f"Scatter: two numeric columns '{num_cols[0]}' (X) vs '{num_cols[1]}' (Y)."),
            confidence=0.8,
        )

    # ── Rule 3: Pie chart ─────────────────────────────────────────────
    # For very small cardinality (2-4) where proportions are clear.
    # Comes before BAR because small-N categorical+num is often
    # better shown as proportional breakdown.
    if cat_cols and num_cols:
        for cat in cat_cols:
            card = _cardinality(_extract_values(rows, cat))
            if 2 <= card <= 4:
                num = num_cols[0]
                return ChartConfig(
                    chart_type=ChartType.PIE,
                    title=_title_from_question(question),
                    x=AxisConfig(column=cat, label=cat),
                    y=AxisConfig(column=num, label=num),
                    reasoning=(
                        f"Pie chart: categorical '{cat}' has "
                        f"{card} unique values (≤4), "
                        f"numeric '{num}' for values."
                    ),
                    confidence=0.9,
                )

    # ── Rule 4: Bar chart (primary categorical) ───────────────────────
    # Handles 3-30 categories — the most common case.
    if cat_cols and num_cols:
        cat = cat_cols[0]
        card = _cardinality(_extract_values(rows, cat))
        num = num_cols[0]

        if 3 <= card <= max_bar_categories:
            orientation = "h" if card > 10 else "v"
            return ChartConfig(
                chart_type=ChartType.BAR,
                title=_title_from_question(question),
                x=AxisConfig(column=cat, label=cat),
                y=AxisConfig(column=num, label=num),
                orientation=orientation,
                reasoning=(
                    f"Bar chart: categorical '{cat}' ({card} values) "
                    f"on X, numeric '{num}' on Y. "
                    f"Orientation: {orientation}."
                ),
                confidence=0.85,
            )

    # ── Rule 5: Area chart (high-cardinality categorical) ─────────────
    # After bar and pie have been tried — for >30 categories or
    # when bar didn't match cardinality threshold.
    if cat_cols and num_cols:
        cat = cat_cols[0]
        card = _cardinality(_extract_values(rows, cat))
        num = num_cols[0]

        if card > max_bar_categories:
            return ChartConfig(
                chart_type=ChartType.AREA,
                title=_title_from_question(question),
                x=AxisConfig(column=cat, label=cat),
                y=AxisConfig(column=num, label=num),
                reasoning=(
                    f"Area chart: categorical '{cat}' with {card} unique "
                    f"values (>{max_bar_categories}), numeric '{num}' on Y."
                ),
                confidence=0.6,
            )

    # ── Rule 6: Single numeric → table (can't visualise) ──────────────
    if num_cols and not cat_cols and not dt_cols:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title=_title_from_question(question),
            reasoning="Only numeric columns found without categorical/datetime — table fallback.",
            confidence=0.3,
        )

    # ── Rule 6: Categorical only → table ──────────────────────────────
    if cat_cols and not num_cols and not dt_cols:
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title=_title_from_question(question),
            reasoning="Only categorical columns — table fallback.",
            confidence=0.2,
        )

    # ── Fallback ──────────────────────────────────────────────────────
    return ChartConfig(
        chart_type=ChartType.TABLE,
        title=_title_from_question(question),
        reasoning="No clear chart type matched — table fallback.",
        confidence=0.1,
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _title_from_question(question: str) -> str:
    """Derive a short chart title from the NL question."""
    if not question:
        return ""
    # Take first ~80 chars, clean up
    title = question.strip().rstrip("?")
    if len(title) > 80:
        title = title[:77] + "..."
    return title
