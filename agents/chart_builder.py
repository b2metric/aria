"""Chart Builder — full heuristic/LLM → payload pipeline.

Orchestrates the chart lifecycle:
  1. Heuristic chart proposer (zero LLM) — always runs
  2. LLM chart proposer (optional escalation) — refines or overrides
  3. JSON payload renderer — API output for Recharts
  4. (Optional) CSV/PNG renderer for static history/export

Architecture mirrors ``agents/sql_pipeline``:
  - ``ChartPipelineResult`` — unified output dataclass
  - ``run_chart_pipeline()`` — async full pipeline
  - ``run_chart_pipeline_sync()`` — sync convenience wrapper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from agents.chart_renderer import RenderOutput

from agents.chart_heuristic import propose_chart
from agents.chart_llm import propose_chart_llm_with_heuristic
from agents.chart_renderer import render_csv, render_json, render_png
from agents.chart_types import ChartConfig, ChartType

log = structlog.get_logger(__name__)


@dataclass
class ChartPipelineResult:
    """Complete output of a chart pipeline run."""

    config: ChartConfig
    """Final chart configuration (heuristic or LLM)."""

    source: str = "heuristic"
    """How the config was determined: 'heuristic' or 'llm'."""

    json: RenderOutput | None = None
    """JSON chart output (config + data) for frontend UI."""

    png: RenderOutput | None = None
    """PNG chart output."""

    csv: RenderOutput | None = None
    """CSV data output."""

    errors: list[str] = field(default_factory=list)
    """Non-fatal errors encountered during rendering."""

    usage: dict | None = None
    """Token usage of the chart LLM call (``{prompt_tokens, completion_tokens, model}``),
    or None when the heuristic was used / the LLM call failed. For metering."""

    @property
    def json_content(self) -> str | None:
        """Get JSON content as string, or None."""
        if self.json and self.json.content:
            return self.json.content if isinstance(self.json.content, str) else None
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


async def run_chart_pipeline(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    use_llm: bool = False,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
    render_formats: tuple[str, ...] = ("json", "csv"),
    output_dir: str | None = None,
    base_name: str = "chart",
) -> ChartPipelineResult:
    """Run the full chart pipeline: propose → render."""
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

    # 1: Heuristic proposer
    config = propose_chart(rows, columns=columns, question=question)
    source = "heuristic"

    # 2: LLM escalation (optional)
    usage: dict | None = None
    if use_llm:
        try:
            config, usage = await propose_chart_llm_with_heuristic(
                rows,
                columns=columns,
                question=question,
                model_name=model_name,
                llm_base_url=llm_base_url,
                llm_api_key=llm_api_key,
            )
            source = "llm"
        except Exception as exc:
            log.error("chart_pipeline.llm_failed", error=str(exc))
            errors.append(f"LLM proposal failed: {exc} — using heuristic fallback")

    # 3: Render
    json_out = None
    png_out = None
    csv_out = None

    if "json" in render_formats:
        try:
            json_out = render_json(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.json" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"JSON render failed: {exc}")

    if "png" in render_formats:
        try:
            png_out = render_png(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.png" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"PNG render failed: {exc}")

    if "csv" in render_formats:
        try:
            csv_out = render_csv(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.csv" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"CSV render failed: {exc}")

    return ChartPipelineResult(
        config=config,
        source=source,
        json=json_out,
        png=png_out,
        csv=csv_out,
        errors=errors,
        usage=usage,
    )


def run_chart_pipeline_sync(
    rows: list[dict],
    *,
    columns: list[str] | None = None,
    question: str = "",
    use_llm: bool = False,
    model_name: str | None = None,
    llm_base_url: str = "http://localhost:4000/v1",
    llm_api_key: str = "",
    render_formats: tuple[str, ...] = ("json", "csv"),
    output_dir: str | None = None,
    base_name: str = "chart",
) -> ChartPipelineResult:
    """Synchronous wrapper around run_chart_pipeline."""
    import asyncio

    if not use_llm:
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
        asyncio.get_running_loop()
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
    render_formats: tuple[str, ...] = ("json", "csv"),
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

    json_out = None
    png_out = None
    csv_out = None

    if "json" in render_formats:
        try:
            json_out = render_json(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.json" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"JSON render failed: {exc}")

    if "png" in render_formats:
        try:
            png_out = render_png(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.png" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"PNG render failed: {exc}")

    if "csv" in render_formats:
        try:
            csv_out = render_csv(
                rows,
                config,
                columns=columns,
                output_path=f"{output_dir}/{base_name}.csv" if output_dir else None,
            )
        except Exception as exc:
            errors.append(f"CSV render failed: {exc}")

    return ChartPipelineResult(
        config=config,
        source="heuristic",
        json=json_out,
        png=png_out,
        csv=csv_out,
        errors=errors,
    )
