"""Chart renderer — JSON, CSV, and PNG export.

Takes a ``ChartConfig`` + data rows and exports it for the UI:
  - **JSON**: standard payload for Recharts on the Next.js frontend (contains config + data)
  - **CSV**: raw data export for history/downloads
  - **PNG**: (optional) static image generated via Plotly/Kaleido for static history

Next.js frontend exclusively uses JSON payload + Recharts for interactive rendering.
Plotly HTML iframe rendering has been removed to comply with architecture rules.
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

import structlog

from agents.chart_types import ChartConfig, ChartType

log = structlog.get_logger(__name__)


@dataclass
class RenderOutput:
    """Output from a single render call."""

    format: str
    """One of: json, csv, png."""

    path: str | None = None
    """File path if written to disk, or None if in-memory."""

    content: str | bytes | None = None
    """In-memory content (str for json/csv, bytes for png)."""

    size_bytes: int = 0
    """Size of the output in bytes."""


def render_json(
    rows: list[dict],
    config: ChartConfig,
    *,
    columns: list[str] | None = None,
    output_path: str | None = None,
) -> RenderOutput:
    """Render chart configuration and data as a JSON payload for Recharts."""
    if columns is None and rows:
        columns = list(rows[0].keys())
    elif columns is None:
        columns = []

    import dataclasses

    payload = {
        "chart_config": dataclasses.asdict(config),
        "chart_data": rows,
        "columns": columns,
    }

    json_str = json.dumps(payload, default=str)
    size = len(json_str.encode("utf-8"))

    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
        log.info("chart_renderer.json_written", path=output_path, size=size)
        return RenderOutput(format="json", path=output_path, size_bytes=size)

    return RenderOutput(format="json", content=json_str, size_bytes=size)


def render_csv(
    rows: list[dict],
    config: ChartConfig | None = None,
    *,
    columns: list[str] | None = None,
    output_path: str | None = None,
    delimiter: str = ",",
    include_bom: bool = True,
) -> RenderOutput:
    """Export data as CSV."""
    if not rows:
        return RenderOutput(format="csv", content="", size_bytes=0)

    if columns is None:
        columns = list(rows[0].keys())

    buf = io.StringIO()
    if include_bom:
        buf.write("\ufeff")

    writer = csv.DictWriter(
        buf,
        fieldnames=columns,
        delimiter=delimiter,
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writeheader()
    writer.writerows(rows)

    csv_str = buf.getvalue()
    size = len(csv_str.encode("utf-8"))

    if output_path:
        Path(output_path).write_text(csv_str, encoding="utf-8")
        log.info("chart_renderer.csv_written", path=output_path, size=size)
        return RenderOutput(format="csv", path=output_path, size_bytes=size)

    return RenderOutput(format="csv", content=csv_str, size_bytes=size)


def render_png(
    rows: list[dict],
    config: ChartConfig,
    *,
    columns: list[str] | None = None,
    output_path: str | None = None,
    width: int = 1200,
    height: int = 700,
    scale: int = 2,
) -> RenderOutput:
    """Render chart as a PNG image via Kaleido & Plotly.

    Requires ``kaleido`` and ``plotly`` packages (used only for static export).
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        log.warning("chart_renderer.plotly_missing", action="skip_png")
        return RenderOutput(format="png", content=None, size_bytes=0)

    if columns is None and rows:
        columns = list(rows[0].keys())
    elif columns is None:
        columns = []

    ct = config.chart_type
    x_col = config.x.column or (columns[0] if columns else "")
    y_col = config.y.column or (columns[1] if len(columns) > 1 else (columns[0] if columns else ""))

    x_vals = [row.get(x_col) for row in rows] if x_col else []
    y_vals = [row.get(y_col) for row in rows] if y_col else []

    fig = go.Figure()
    # Simplified rendering purely for background image export
    if ct == ChartType.BAR:
        fig.add_trace(go.Bar(x=x_vals, y=y_vals))
    elif ct == ChartType.LINE:
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="lines+markers"))
    elif ct == ChartType.PIE:
        fig.add_trace(go.Pie(labels=x_vals, values=y_vals))
    elif ct == ChartType.SCATTER:
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="markers"))
    else:
        fig.add_annotation(text="Table View", showarrow=False)

    fig.update_layout(
        title=config.title or "",
        xaxis_title=config.x.label or x_col,
        yaxis_title=config.y.label or y_col,
        template="plotly_white",
    )

    try:
        # Don't pass engine="kaleido": the `engine` arg is deprecated (Plotly
        # removes it after Sept 2025, Kaleido becomes the only/default engine).
        img_bytes: bytes = fig.to_image(
            format="png",
            width=width,
            height=height,
            scale=scale,
        )
    except Exception as e:
        log.warning("chart_renderer.kaleido_failed", error=str(e))
        return RenderOutput(format="png", content=None, size_bytes=0)

    size = len(img_bytes)
    if output_path:
        Path(output_path).write_bytes(img_bytes)
        log.info("chart_renderer.png_written", path=output_path, size=size)
        return RenderOutput(format="png", path=output_path, size_bytes=size)

    return RenderOutput(format="png", content=img_bytes, size_bytes=size)


def render_all(
    rows: list[dict],
    config: ChartConfig,
    *,
    columns: list[str] | None = None,
    output_dir: str | None = None,
    base_name: str = "chart",
) -> dict[str, RenderOutput]:
    """Render JSON, PNG, and CSV formats."""
    results: dict[str, RenderOutput] = {}

    json_path = os.path.join(output_dir, f"{base_name}.json") if output_dir else None
    png_path = os.path.join(output_dir, f"{base_name}.png") if output_dir else None
    csv_path = os.path.join(output_dir, f"{base_name}.csv") if output_dir else None

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    results["json"] = render_json(rows, config, columns=columns, output_path=json_path)
    results["csv"] = render_csv(rows, config, columns=columns, output_path=csv_path)
    results["png"] = render_png(rows, config, columns=columns, output_path=png_path)

    return results
