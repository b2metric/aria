"""Chart type enumeration and configuration model.

Mirrors bi-indexer's ChartDraft pattern — the canonical schema that
downstream renderers and exporters consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChartType(str, Enum):
    """Supported chart types.

    Case-insensitive from string: ``ChartType("TABLE")`` works.
    """

    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"
    AREA = "area"
    TABLE = "table"

    @classmethod
    def _missing_(cls, value: object) -> "ChartType | None":
        if isinstance(value, str):
            lower = value.lower()
            for member in cls:
                if member.value == lower:
                    return member
        return None


@dataclass
class AxisConfig:
    """Configuration for a chart axis."""
    column: str = ""
    """Column name to use for this axis."""
    label: str = ""
    """Human-readable axis label (defaults to column name)."""
    log_scale: bool = False
    """Whether to use logarithmic scale."""


@dataclass
class ChartConfig:
    """Chart configuration produced by heuristic or LLM proposer.

    This is the canonical config that ChartRenderer consumes.  It is
    serialisable to JSON for caching/logging and carries enough
    information to render a Plotly figure without further decisions.
    """

    chart_type: ChartType = ChartType.TABLE
    """Selected chart type."""

    title: str = ""
    """Chart title (auto-generated if empty)."""

    x: AxisConfig = field(default_factory=AxisConfig)
    """X-axis configuration."""

    y: AxisConfig = field(default_factory=AxisConfig)
    """Y-axis configuration."""

    color_column: str = ""
    """Optional column for colour grouping / series split."""

    labels: dict[str, str] = field(default_factory=dict)
    """Column name → human-readable label mapping."""

    limits: dict[str, Any] = field(default_factory=dict)
    """Axis limits, e.g. {'x': [0, 100], 'y': [0, None]}."""

    # ── Display hints ──────────────────────────────────────────────────

    orientation: str = "v"
    """Bar orientation: 'v' (vertical) or 'h' (horizontal)."""

    stacked: bool = False
    """Whether bars/areas should be stacked."""

    show_legend: bool = True
    """Whether to display the legend."""

    # ── Metadata ───────────────────────────────────────────────────────

    confidence: float = 1.0
    """Confidence score (0=guess, 1=certain).  Always 1.0 for heuristic."""

    reasoning: str = ""
    """Human-readable explanation for why this chart type was chosen."""
