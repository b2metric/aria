"""Chart Builder + Plotly Pipeline test suite.

Covers:
  - ChartType enum and ChartConfig dataclass
  - Heuristic chart proposer (all chart types + edge cases)
  - Plotly HTML/CSV renderer
  - Chart builder pipeline (heuristic path)
  - Public API exports
"""

from __future__ import annotations

import csv
import io
import os
import tempfile

import pytest

from agents.chart_types import AxisConfig, ChartConfig, ChartType
from agents.chart_heuristic import (
    _cardinality,
    _is_datetime,
    _is_numeric,
    _classify_columns,
    propose_chart,
)
from agents.chart_renderer import (
    render_all,
    render_csv,
    render_json,
)
from agents.chart_builder import (
    ChartPipelineResult,
    run_chart_pipeline_sync,
)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sales_data() -> list[dict]:
    """Bar chart: category + numeric."""
    return [
        {"product": "Widget", "revenue": 15000},
        {"product": "Gadget", "revenue": 23000},
        {"product": "Doohickey", "revenue": 8700},
        {"product": "Thingamajig", "revenue": 19200},
        {"product": "Whatchamacallit", "revenue": 31000},
    ]


@pytest.fixture
def time_series_data() -> list[dict]:
    """Line chart: datetime + numeric."""
    return [
        {"date": "2024-01-01", "users": 120},
        {"date": "2024-02-01", "users": 145},
        {"date": "2024-03-01", "users": 190},
        {"date": "2024-04-01", "users": 210},
        {"date": "2024-05-01", "users": 250},
    ]


@pytest.fixture
def scatter_data() -> list[dict]:
    """Scatter: two numeric columns."""
    return [
        {"spend": 100, "roi": 1.2},
        {"spend": 200, "roi": 1.5},
        {"spend": 350, "roi": 2.1},
        {"spend": 500, "roi": 2.8},
        {"spend": 800, "roi": 3.5},
    ]


@pytest.fixture
def pie_data() -> list[dict]:
    """Pie chart: low-cardinality categorical + numeric."""
    return [
        {"channel": "Organic", "visitors": 4500},
        {"channel": "Paid", "visitors": 2300},
        {"channel": "Referral", "visitors": 1200},
        {"channel": "Social", "visitors": 800},
    ]


@pytest.fixture
def large_data() -> list[dict]:
    """Data exceeding table thresholds for table fallback."""
    return [
        {"col_a": i, "col_b": f"val_{i}", "col_c": i * 1.5}
        for i in range(300)
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ChartType enum
# ═══════════════════════════════════════════════════════════════════════════


class TestChartType:
    def test_all_values_present(self):
        assert ChartType.BAR.value == "bar"
        assert ChartType.LINE.value == "line"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.PIE.value == "pie"
        assert ChartType.AREA.value == "area"
        assert ChartType.TABLE.value == "table"

    def test_from_string(self):
        assert ChartType("bar") == ChartType.BAR
        assert ChartType("line") == ChartType.LINE
        assert ChartType("TABLE") == ChartType.TABLE

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            ChartType("histogram")


# ═══════════════════════════════════════════════════════════════════════════
# ChartConfig dataclass
# ═══════════════════════════════════════════════════════════════════════════


class TestChartConfig:
    def test_defaults(self):
        cfg = ChartConfig()
        assert cfg.chart_type == ChartType.TABLE
        assert cfg.confidence == 1.0
        assert cfg.title == ""

    def test_full_config(self):
        cfg = ChartConfig(
            chart_type=ChartType.BAR,
            title="Revenue by Product",
            x=AxisConfig(column="product", label="Product Name"),
            y=AxisConfig(column="revenue", label="Revenue ($)"),
            orientation="v",
            stacked=True,
            confidence=0.95,
            reasoning="Clear categorical grouping.",
        )
        assert cfg.chart_type == ChartType.BAR
        assert cfg.x.column == "product"
        assert cfg.y.column == "revenue"
        assert cfg.orientation == "v"
        assert cfg.stacked is True

    def test_axis_limits(self):
        cfg = ChartConfig(
            chart_type=ChartType.SCATTER,
            limits={"x": [0, 100], "y": [0, None]},
        )
        assert cfg.limits["x"] == [0, 100]
        assert cfg.limits["y"] == [0, None]


# ═══════════════════════════════════════════════════════════════════════════
# Heuristic helpers
# ═══════════════════════════════════════════════════════════════════════════


class TestHeuristicHelpers:
    def test_is_numeric_int(self):
        assert _is_numeric([1, 2, 3]) is True

    def test_is_numeric_float(self):
        assert _is_numeric([1.5, 2.3, 3.7]) is True

    def test_is_numeric_string(self):
        assert _is_numeric(["1.5", "2.3"]) is True

    def test_is_numeric_false(self):
        assert _is_numeric(["a", "b", "c"]) is False

    def test_is_numeric_with_none(self):
        assert _is_numeric([1, None, 3]) is True

    def test_is_datetime_iso(self):
        assert _is_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]) is True

    def test_is_datetime_slash(self):
        assert _is_datetime(["01/01/2024", "02/01/2024"]) is True

    def test_is_datetime_false(self):
        assert _is_datetime(["hello", "world"]) is False

    def test_cardinality(self):
        assert _cardinality(["a", "b", "a", "c"]) == 3

    def test_cardinality_with_none(self):
        assert _cardinality(["a", None, "b", None]) == 2

    def test_classify_columns(self, sales_data):
        classified = _classify_columns(sales_data, ["product", "revenue"])
        assert "product" in classified["categorical"]
        assert "revenue" in classified["numeric"]


# ═══════════════════════════════════════════════════════════════════════════
# Heuristic chart proposer
# ═══════════════════════════════════════════════════════════════════════════


class TestHeuristicProposer:
    def test_bar_chart(self, sales_data):
        cfg = propose_chart(sales_data)
        assert cfg.chart_type == ChartType.BAR
        assert cfg.x.column == "product"
        assert cfg.y.column == "revenue"
        assert cfg.confidence >= 0.8

    def test_line_chart(self, time_series_data):
        cfg = propose_chart(time_series_data)
        assert cfg.chart_type == ChartType.LINE
        assert cfg.x.column == "date"
        assert cfg.y.column == "users"
        assert cfg.confidence >= 0.8

    def test_scatter_chart(self, scatter_data):
        cfg = propose_chart(scatter_data)
        assert cfg.chart_type == ChartType.SCATTER
        assert cfg.confidence >= 0.7

    def test_pie_chart(self, pie_data):
        cfg = propose_chart(pie_data)
        assert cfg.chart_type == ChartType.PIE
        assert cfg.x.column == "channel"
        assert cfg.y.column == "visitors"
        assert cfg.confidence >= 0.8

    def test_table_fallback_large_rows(self, large_data):
        cfg = propose_chart(large_data)
        assert cfg.chart_type == ChartType.TABLE

    def test_empty_data(self):
        cfg = propose_chart([])
        assert cfg.chart_type == ChartType.TABLE
        assert cfg.confidence == 0.0

    def test_reasoning_included(self, sales_data):
        cfg = propose_chart(sales_data)
        assert len(cfg.reasoning) > 0

    def test_title_from_question(self, sales_data):
        cfg = propose_chart(sales_data, question="Show me revenue by product category")
        assert len(cfg.title) > 0
        assert "?" not in cfg.title

    def test_bar_orientation_horizontal(self):
        """Many categories → horizontal bars."""
        data = [{"name": f"item_{i}", "value": i * 10} for i in range(15)]
        cfg = propose_chart(data)
        assert cfg.chart_type == ChartType.BAR
        assert cfg.orientation == "h"


# ═══════════════════════════════════════════════════════════════════════════
# Chart renderer — HTML
# ═══════════════════════════════════════════════════════════════════════════


class TestRendererJSON:
    def test_bar_json(self, sales_data):
        cfg = propose_chart(sales_data)
        out = render_json(sales_data, cfg)
        assert out.format == "json"
        assert out.content is not None
        content = out.content if isinstance(out.content, str) else ""
        assert '"chart_data"' in content and '"chart_config"' in content
        assert out.size_bytes > 0

    def test_table_json(self, large_data):
        cfg = ChartConfig(chart_type=ChartType.TABLE, title="Big Data")
        out = render_json(large_data[:10], cfg)
        content = out.content if isinstance(out.content, str) else ""
        assert '"chart_type": "table"' in content and '"chart_data"' in content

    def test_html_to_file(self, sales_data):
        cfg = propose_chart(sales_data)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            out = render_json(sales_data, cfg, output_path=path)
            assert out.path == path
            assert os.path.exists(path)
            content = open(path).read()
            assert len(content) > 0
        finally:
            os.unlink(path)

    def test_line_html(self, time_series_data):
        cfg = propose_chart(time_series_data)
        out = render_json(time_series_data, cfg)
        assert cfg.chart_type == ChartType.LINE
        assert out.content is not None

    def test_scatter_html(self, scatter_data):
        cfg = propose_chart(scatter_data)
        out = render_json(scatter_data, cfg)
        assert cfg.chart_type == ChartType.SCATTER
        assert out.content is not None

    def test_pie_html(self, pie_data):
        cfg = propose_chart(pie_data)
        out = render_json(pie_data, cfg)
        assert cfg.chart_type == ChartType.PIE
        assert out.content is not None


# ═══════════════════════════════════════════════════════════════════════════
# Chart renderer — CSV
# ═══════════════════════════════════════════════════════════════════════════


class TestRendererCSV:
    def test_csv_content(self, sales_data):
        out = render_csv(sales_data)
        assert out.format == "csv"
        content = out.content if isinstance(out.content, str) else ""
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
        rows = list(reader)
        assert len(rows) == 5
        assert rows[0]["product"] == "Widget"

    def test_csv_to_file(self, sales_data):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            out = render_csv(sales_data, output_path=path)
            assert out.path == path
            assert os.path.exists(path)
            content = open(path).read()
            assert "product" in content
        finally:
            os.unlink(path)

    def test_csv_empty(self):
        out = render_csv([])
        assert out.size_bytes == 0

    def test_csv_bom(self, sales_data):
        out = render_csv(sales_data, include_bom=True)
        content = out.content if isinstance(out.content, str) else ""
        assert content.startswith("\ufeff")

    def test_csv_no_bom(self, sales_data):
        out = render_csv(sales_data, include_bom=False)
        content = out.content if isinstance(out.content, str) else ""
        assert not content.startswith("\ufeff")
        assert content.startswith("product")


# ═══════════════════════════════════════════════════════════════════════════
# Chart renderer — render_all
# ═══════════════════════════════════════════════════════════════════════════


class TestRenderAll:
    def test_render_all_to_dir(self, sales_data):
        cfg = propose_chart(sales_data)
        with tempfile.TemporaryDirectory() as tmpdir:
            results = render_all(sales_data, cfg, output_dir=tmpdir, base_name="test")
            assert "json" in results
            assert "csv" in results
            json_path = os.path.join(tmpdir, "test.json")
            assert os.path.exists(json_path)
            csv_path = os.path.join(tmpdir, "test.csv")
            assert os.path.exists(csv_path)

    def test_render_all_in_memory(self, sales_data):
        cfg = propose_chart(sales_data)
        results = render_all(sales_data, cfg)
        assert results["json"].content is not None
        assert results["csv"].content is not None


# ═══════════════════════════════════════════════════════════════════════════
# Chart pipeline
# ═══════════════════════════════════════════════════════════════════════════


class TestChartPipeline:
    def test_pipeline_sync_bar(self, sales_data):
        result = run_chart_pipeline_sync(sales_data, question="Revenue by product")
        assert isinstance(result, ChartPipelineResult)
        assert result.source == "heuristic"
        assert result.config.chart_type == ChartType.BAR
        assert result.json is not None
        assert result.csv is not None
        assert len(result.errors) == 0

    def test_pipeline_sync_line(self, time_series_data):
        result = run_chart_pipeline_sync(time_series_data)
        assert result.config.chart_type == ChartType.LINE
        assert result.json is not None
        assert result.csv is not None

    def test_pipeline_sync_pie(self, pie_data):
        result = run_chart_pipeline_sync(pie_data)
        assert result.config.chart_type == ChartType.PIE

    def test_pipeline_sync_scatter(self, scatter_data):
        result = run_chart_pipeline_sync(scatter_data)
        assert result.config.chart_type == ChartType.SCATTER

    def test_pipeline_sync_table(self, large_data):
        result = run_chart_pipeline_sync(large_data)
        assert result.config.chart_type == ChartType.TABLE

    def test_pipeline_empty_data(self):
        result = run_chart_pipeline_sync([])
        assert result.config.chart_type == ChartType.TABLE
        assert result.config.confidence == 0.0
        assert len(result.errors) > 0

    def test_pipeline_json_content(self, sales_data):
        result = run_chart_pipeline_sync(sales_data)
        assert result.json_content is not None
        assert len(result.json_content) > 0

    def test_pipeline_csv_content(self, sales_data):
        result = run_chart_pipeline_sync(sales_data)
        assert result.csv_content is not None
        assert "product" in result.csv_content

    def test_pipeline_no_png_by_default(self, sales_data):
        result = run_chart_pipeline_sync(sales_data)
        assert result.png is None

    def test_pipeline_to_files(self, sales_data):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_chart_pipeline_sync(
                sales_data,
                output_dir=tmpdir,
                base_name="sales",
                render_formats=("json", "csv"),
            )
            assert os.path.exists(os.path.join(tmpdir, "sales.json"))
            assert os.path.exists(os.path.join(tmpdir, "sales.csv"))


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


class TestPublicAPI:
    def test_imports(self):
        """All public API symbols are importable."""
        from agents import (
            AxisConfig,
            ChartConfig,
            ChartType,
            ChartPipelineResult,
            propose_chart_heuristic,
            propose_chart_llm,
            propose_chart_llm_with_heuristic,
            LlmChartChoice,
            render_json,
            render_csv,
            render_all,
            RenderOutput,
            run_chart_pipeline,
            run_chart_pipeline_sync,
        )
        # Just verifying no ImportError

    def test_chart_type_values(self):
        """All chart types are available."""
        types_list = [ChartType.BAR, ChartType.LINE, ChartType.SCATTER,
                      ChartType.PIE, ChartType.AREA, ChartType.TABLE]
        assert len(types_list) == 6
        assert all(isinstance(t, ChartType) for t in types_list)


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_single_column_numeric(self):
        data = [{"val": 10}, {"val": 20}, {"val": 30}]
        cfg = propose_chart(data)
        assert cfg.chart_type == ChartType.TABLE

    def test_single_column_categorical(self):
        data = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        cfg = propose_chart(data)
        assert cfg.chart_type == ChartType.TABLE

    def test_all_null_column(self):
        data = [{"col": None}, {"col": None}]
        cfg = propose_chart(data)
        assert cfg.chart_type == ChartType.TABLE

    def test_mixed_types(self):
        data = [
            {"category": "A", "value": 10, "date": "2024-01-01"},
            {"category": "B", "value": 20, "date": "2024-02-01"},
        ]
        cfg = propose_chart(data)
        # date column detected as datetime → line chart takes priority
        assert cfg.chart_type == ChartType.LINE
