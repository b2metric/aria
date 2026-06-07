"""Chart Builder — full heuristic/LLM → Plotly pipeline.

Orchestrates the chart lifecycle:
  1. Heuristic chart proposer (zero LLM) — always runs
  2. LLM chart proposer (optional escalation) — refines or overrides
  3. Plotly renderer — HTML, PNG, CSV export

Architecture mirrors ``agents/sql_pipeline``:
  - ``ChartPipelineResult`` — unified output dataclass
  - ``run_chart_pipeline()`` — async full pipeline
  - ``run_chart_pipeline_sync()`` — sync convenience wrapper

Usage::

    from agents.chart_builder import run_chart_pipeline_sync

    result = run_chart_pipeline_sync(
        rows=[{"category": "A", "value": 10}, ...],
        question="Sales by category",
    )
    # result.html_output, result.csv_output, result.config are all set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from agents.chart_llm import LlmChartChoice
    from agents.chart_renderer import RenderOutput

from agents.chart_heuristic import propose_chart
from agents.chart_llm import propose_chart_llm_with_heuristic
from agents.chart_renderer import render_all, render_csv, render_html, render_png
from agents.chart_types import ChartConfig, ChartType

log = structlog.get_logger(__name__)


# ── Pipeline result ────────────────────────────────────────────────────────


@dataclass
class ChartPipelineResult:
    """Complete output of a chart pipeline run."""

    config: ChartConfig
    """Final chart configuration (heuristic or LLM)."""

    source: str = "heuristic"
    """How the config was determined: 'heuristic' or 'llm'."""

    html: "RenderOutput | None" = None
    """HTML chart output."""

    png: "RenderOutput | None" = None
    """PNG chart output."""

    csv: "RenderOutput | None" = None
    """CSV data output."""

    errors: list[str] = field(default_factory=list)
    """Non-fatal errors encountered during rendering."""

    @property
    def html_content(self) -> str | None:
        """Get HTML content as string, or None."""
        if self.html and self.html.content:
            return self.html.content if isinstance(self.html.content, str) else None
        return None

    @property
    def png_bytes(self) -> bytes | None:
        """Get PNG content as bytes, or None."""
        if self.png and self.png.content:
            return self.png.content if isinstance(self.png.content, bytes) else None
        return None

    @property
    def csv_content(self) -> str | None:
        """Get CSV content as string, or None."""
        if self.csv and self.csv.content:
            return self.csv.content if isinstance(self.csv.content, str) else None
        return None


# ── Pipeline ───────────────────────────────────────────────────────────────


async def run_chart_pipeline(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    use_llm: bool = False,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
    render_formats: tuple[str, ...] = ("html", "csv"),
    output_dir: str | None = None,
    base_name: str = "chart",
) -> ChartPipelineResult:
    """Run the full chart pipeline: propose → render.

    Args:
        rows: Query result rows as list of dicts.
        columns: Ordered column names (inferred from first row if None).
        question: Natural-language question for context.
        use_llm: If True, escalate to LLM after heuristic.
        model_name: LLM model override.
        llm_base_url: API endpoint.
        llm_api_key: API key.
        render_formats: Which formats to render ('html', 'png', 'csv').
        output_dir: Directory to write rendered files.
        base_name: Base filename for rendered files.

    Returns:
        ChartPipelineResult with config and rendered outputs.
    """
    if not rows:
        log.warning("chart_pipeline.empty_data")
        return ChartPipelineResult(
            config=ChartConfig(chart_type=ChartType.TABLE, confidence=0.0),
            source="heuristic",
            errors=["No data rows provided"],
        )

    if columns is None:
        columns = list(rows[0].keys())

    errors: list[str] = []

    # ── Stage 1: Heuristic proposer ────────────────────────────────────
    config = propose_chart(rows, columns=columns, question=question)
    source = "heuristic"

    log.info(
        "chart_pipeline.heuristic",
        chart_type=config.chart_type.value,
        confidence=config.confidence,
        x=config.x.column,
        y=config.y.column,
    )

    # ── Stage 2: LLM escalation (optional) ─────────────────────────────
    if use_llm:
        try:
            config = await propose_chart_llm_with_heuristic(
                rows,
                columns=columns,
                question=question,
                model_name=model_name,
                llm_base_url=llm_base_url,
                llm_api_key=llm_api_key,
            )
            source = "llm"
            log.info(
                "chart_pipeline.llm_override",
                chart_type=config.chart_type.value,
                confidence=config.confidence,
            )
        except Exception as exc:
            log.error("chart_pipeline.llm_failed", error=str(exc))
            errors.append(f"LLM proposal failed: {exc} — using heuristic fallback")
            # Keep heuristic config

    # ── Stage 3: Render ────────────────────────────────────────────────
    html_out = None
    png_out = None
    csv_out = None

    if "html" in render_formats:
        try:
            html_out = render_html(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.html" if output_dir else None
                ),
            )
        except Exception as exc:
            log.error("chart_pipeline.html_failed", error=str(exc))
            errors.append(f"HTML render failed: {exc}")

    if "png" in render_formats:
        try:
            png_out = render_png(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.png" if output_dir else None
                ),
            )
        except Exception as exc:
            log.error("chart_pipeline.png_failed", error=str(exc))
            errors.append(f"PNG render failed: {exc}")

    if "csv" in render_formats:
        try:
            csv_out = render_csv(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.csv" if output_dir else None
                ),
            )
        except Exception as exc:
            log.error("chart_pipeline.csv_failed", error=str(exc))
            errors.append(f"CSV render failed: {exc}")

    result = ChartPipelineResult(
        config=config,
        source=source,
        html=html_out,
        png=png_out,
        csv=csv_out,
        errors=errors,
    )

    log.info(
        "chart_pipeline.complete",
        source=source,
        chart_type=config.chart_type.value,
        html_ok=html_out is not None,
        png_ok=png_out is not None,
        csv_ok=csv_out is not None,
        errors=len(errors),
    )

    return result


# ── Sync convenience wrapper ───────────────────────────────────────────────


def run_chart_pipeline_sync(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    use_llm: bool = False,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
    render_formats: tuple[str, ...] = ("html", "csv"),
    output_dir: str | None = None,
    base_name: str = "chart",
) -> ChartPipelineResult:
    """Synchronous wrapper around run_chart_pipeline."""
    import asyncio

    if not use_llm:
        # Fast path: no async needed
        return _run_sync(
            rows,
            columns=columns,
            question=question,
            render_formats=render_formats,
            output_dir=output_dir,
            base_name=base_name,
        )

    coro = run_chart_pipeline(
        rows,
        columns=columns,
        question=question,
        use_llm=True,
        model_name=model_name,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        render_formats=render_formats,
        output_dir=output_dir,
        base_name=base_name,
    )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


def _run_sync(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    render_formats: tuple[str, ...] = ("html", "csv"),
    output_dir: str | None = None,
    base_name: str = "chart",
) -> ChartPipelineResult:
    """Pure sync path for heuristic-only pipeline."""
    if not rows:
        return ChartPipelineResult(
            config=ChartConfig(chart_type=ChartType.TABLE, confidence=0.0),
            source="heuristic",
            errors=["No data rows provided"],
        )

    if columns is None:
        columns = list(rows[0].keys())

    config = propose_chart(rows, columns=columns, question=question)
    errors: list[str] = []

    html_out = None
    png_out = None
    csv_out = None

    if "html" in render_formats:
        try:
            html_out = render_html(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.html" if output_dir else None
                ),
            )
        except Exception as exc:
            errors.append(f"HTML render failed: {exc}")

    if "png" in render_formats:
        try:
            png_out = render_png(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.png" if output_dir else None
                ),
            )
        except Exception as exc:
            errors.append(f"PNG render failed: {exc}")

    if "csv" in render_formats:
        try:
            csv_out = render_csv(
                rows, config, columns=columns,
                output_path=(
                    f"{output_dir}/{base_name}.csv" if output_dir else None
                ),
            )
        except Exception as exc:
            errors.append(f"CSV render failed: {exc}")

    return ChartPipelineResult(
        config=config,
        source="heuristic",
        html=html_out,
        png=png_out,
        csv=csv_out,
        errors=errors,
    )
