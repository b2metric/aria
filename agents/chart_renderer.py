"""Plotly chart renderer — HTML, PNG, and CSV export.

Takes a ``ChartConfig`` + data rows and renders the chart in three
formats:
  - **HTML**: self-contained HTML document with embedded Plotly.js
  - **PNG**: static image via Kaleido (requires ``kaleido`` package)
  - **CSV**: raw data export with optional BOM for Excel compatibility

All render methods are synchronous and accept file paths; if no path
is given they return the in-memory content.

Mirrors bi-indexer's render pipeline: config → Plotly figure → file(s).
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import structlog

from agents.chart_types import ChartConfig, ChartType

log = structlog.get_logger(__name__)


# ── Render output ──────────────────────────────────────────────────────────


@dataclass
class RenderOutput:
    """Output from a single render call."""

    format: str
    """One of: html, png, csv."""

    path: str | None = None
    """File path if written to disk, or None if in-memory."""

    content: str | bytes | None = None
    """In-memory content (str for html/csv, bytes for png)."""

    size_bytes: int = 0
    """Size of the output in bytes."""


# ── Figure builder ─────────────────────────────────────────────────────────


def _build_figure(
    rows: list[dict],
    config: ChartConfig,
    columns: list[str],
) -> go.Figure:
    """Build a Plotly figure from data rows and config."""
    ct = config.chart_type

    x_col = config.x.column or columns[0] if columns else ""
    y_col = config.y.column or (columns[1] if len(columns) > 1 else columns[0])

    # Extract data
    x_vals = [row.get(x_col) for row in rows] if x_col else []
    y_vals = [row.get(y_col) for row in rows] if y_col else []

    title = config.title or ""

    if ct == ChartType.BAR:
        orient = config.orientation or "v"
        if orient == "h":
            fig = go.Figure(go.Bar(
                y=x_vals,
                x=y_vals,
                orientation="h",
                name=y_col,
            ))
        else:
            fig = go.Figure(go.Bar(
                x=x_vals,
                y=y_vals,
                name=y_col,
            ))
        if config.stacked:
            fig.update_layout(barmode="stack")

    elif ct == ChartType.LINE:
        fig = go.Figure(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines+markers",
            name=y_col,
        ))

    elif ct == ChartType.SCATTER:
        fig = go.Figure(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers",
            name=f"{x_col} vs {y_col}",
        ))

    elif ct == ChartType.PIE:
        fig = go.Figure(go.Pie(
            labels=x_vals,
            values=y_vals,
            hole=0.0,
        ))

    elif ct == ChartType.AREA:
        fig = go.Figure(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            fill="tozeroy",
            name=y_col,
        ))
        if config.stacked:
            fig.update_layout(
                hovermode="x unified",
            )

    elif ct == ChartType.TABLE:
        # Table is rendered as CSV, not a Plotly figure
        # Return an empty figure with a note
        fig = go.Figure()
        fig.add_annotation(
            text="Data available as CSV export",
            showarrow=False,
            font={"size": 16},
        )
        title = title or "Table View"

    else:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Unknown chart type: {ct.value}",
            showarrow=False,
        )

    # Apply common layout
    fig.update_layout(
        title=title,
        xaxis_title=config.x.label or config.x.column or x_col,
        yaxis_title=config.y.label or config.y.column or y_col,
        showlegend=config.show_legend,
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 60, "b": 50},
    )

    # Apply axis limits
    if "x" in config.limits:
        x_lim = config.limits["x"]
        if isinstance(x_lim, list) and len(x_lim) == 2:
            fig.update_xaxes(range=x_lim)
    if "y" in config.limits:
        y_lim = config.limits["y"]
        if isinstance(y_lim, list) and len(y_lim) == 2:
            fig.update_yaxes(range=y_lim)

    # Log scale
    if config.x.log_scale:
        fig.update_xaxes(type="log")
    if config.y.log_scale:
        fig.update_yaxes(type="log")

    return fig


# ── Render methods ─────────────────────────────────────────────────────────


def render_html(
    rows: list[dict],
    config: ChartConfig,
    *,
    columns: list[str] | None = None,
    output_path: str | None = None,
    include_plotlyjs: bool | str = True,
    full_html: bool = True,
) -> RenderOutput:
    """Render chart as a self-contained HTML document.

    Args:
        rows: Query result rows.
        config: Chart configuration from heuristic or LLM.
        columns: Ordered column names (inferred if None).
        output_path: File path to write (returns in-memory if None).
        include_plotlyjs: True='cdn', False=omit, str=local path.
        full_html: If True, wrap in <html><head><body>; if False, return
            just the <div> + <script>.

    Returns:
        RenderOutput with format='html'.
    """
    if columns is None and rows:
        columns = list(rows[0].keys())
    elif columns is None:
        columns = []

    fig = _build_figure(rows, config, columns)

    if config.chart_type == ChartType.TABLE:
        # For tables, build an HTML table
        html = _build_html_table(rows, columns, config.title)
    else:
        if full_html:
            html = fig.to_html(
                include_plotlyjs=include_plotlyjs,
                full_html=True,
            )
        else:
            html = fig.to_html(
                include_plotlyjs=include_plotlyjs,
                full_html=False,
            )

    size = len(html.encode("utf-8"))

    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
        log.info("chart_renderer.html_written", path=output_path, size=size)
        return RenderOutput(format="html", path=output_path, size_bytes=size)

    return RenderOutput(format="html", content=html, size_bytes=size)


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
    """Render chart as a PNG image via Kaleido.

    Requires ``kaleido`` package: ``pip install kaleido``.

    Args:
        rows: Query result rows.
        config: Chart configuration.
        columns: Ordered column names.
        output_path: File path (returns in-memory bytes if None).
        width: Image width in pixels.
        height: Image height in pixels.
        scale: Device pixel ratio (2 = retina).

    Returns:
        RenderOutput with format='png'.
    """
    if columns is None and rows:
        columns = list(rows[0].keys())
    elif columns is None:
        columns = []

    fig = _build_figure(rows, config, columns)

    img_bytes: bytes = fig.to_image(
        format="png",
        width=width,
        height=height,
        scale=scale,
        engine="kaleido",
    )

    size = len(img_bytes)

    if output_path:
        Path(output_path).write_bytes(img_bytes)
        log.info("chart_renderer.png_written", path=output_path, size=size)
        return RenderOutput(format="png", path=output_path, size_bytes=size)

    return RenderOutput(format="png", content=img_bytes, size_bytes=size)


def render_csv(
    rows: list[dict],
    config: ChartConfig | None = None,
    *,
    columns: list[str] | None = None,
    output_path: str | None = None,
    delimiter: str = ",",
    include_bom: bool = True,
) -> RenderOutput:
    """Export data as CSV.

    Args:
        rows: Query result rows.
        config: Optional chart config (unused; for API consistency).
        columns: Ordered column names (inferred if None).
        output_path: File path (returns in-memory string if None).
        delimiter: CSV delimiter (default: comma).
        include_bom: Include UTF-8 BOM for Excel compatibility.

    Returns:
        RenderOutput with format='csv'.
    """
    if not rows:
        csv_str = ""
        return RenderOutput(format="csv", content=csv_str, size_bytes=0)

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


# ── Batch render ───────────────────────────────────────────────────────────


def render_all(
    rows: list[dict],
    config: ChartConfig,
    *,
    columns: list[str] | None = None,
    output_dir: str | None = None,
    base_name: str = "chart",
) -> dict[str, RenderOutput]:
    """Render all three formats (HTML, PNG, CSV) at once.

    Args:
        rows: Query result rows.
        config: Chart configuration.
        columns: Ordered column names.
        output_dir: Directory to write files (in-memory if None).
        base_name: Base filename without extension.

    Returns:
        Dict mapping format → RenderOutput.
    """
    results: dict[str, RenderOutput] = {}

    html_path = os.path.join(output_dir, f"{base_name}.html") if output_dir else None
    png_path = os.path.join(output_dir, f"{base_name}.png") if output_dir else None
    csv_path = os.path.join(output_dir, f"{base_name}.csv") if output_dir else None

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    results["html"] = render_html(rows, config, columns=columns, output_path=html_path)
    results["csv"] = render_csv(rows, config, columns=columns, output_path=csv_path)

    try:
        results["png"] = render_png(rows, config, columns=columns, output_path=png_path)
    except Exception as exc:
        log.warning("chart_renderer.png_failed", error=str(exc))
        results["png"] = RenderOutput(
            format="png",
            content=None,
            size_bytes=0,
        )

    log.info(
        "chart_renderer.all_done",
        base=base_name,
        html_size=results["html"].size_bytes,
        csv_size=results["csv"].size_bytes,
        png_ok=results["png"].content is not None or results["png"].path is not None,
    )

    return results


# ── HTML table helper ──────────────────────────────────────────────────────


def _build_html_table(
    rows: list[dict],
    columns: list[str],
    title: str = "",
) -> str:
    """Build a standalone HTML page with a styled table."""
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{title or 'Table View'}</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }",
        "  h1 { color: #333; }",
        "  table { border-collapse: collapse; width: 100%; max-width: 100%; }",
        "  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }",
        "  th { background: #f5f5f5; font-weight: 600; position: sticky; top: 0; }",
        "  tr:hover { background: #f9f9f9; }",
        "  .row-count { color: #888; font-size: 0.9em; margin-bottom: 16px; }",
        "</style>",
        "</head>",
        "<body>",
    ]

    if title:
        lines.append(f"<h1>{title}</h1>")
    lines.append(f'<p class="row-count">{len(rows)} rows × {len(columns)} columns</p>')

    lines.append("<table>")
    lines.append("<thead><tr>")
    for col in columns:
        lines.append(f"<th>{col}</th>")
    lines.append("</tr></thead>")
    lines.append("<tbody>")

    for row in rows:
        lines.append("<tr>")
        for col in columns:
            val = row.get(col, "")
            lines.append(f"<td>{val}</td>")
        lines.append("</tr>")

    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)
