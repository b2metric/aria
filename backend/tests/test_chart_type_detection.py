"""Regression tests for chart-type request detection.

Bug from live logs: a data question like "Show the number of **lines** for each
revenue bucket" forced a *line* chart (substring "line" inside "lines"),
overriding the LLM's correct *bar* choice. Likewise "recharge **table**" would
force a data grid. Detection must be whole-word, and on a new data query must
require an actual visualisation cue (chart/graph/plot/grid), while the
chart-type-only follow-up path ("make it a pie") stays permissive.
"""

from __future__ import annotations

from backend.app.query.pipeline import _detect_requested_chart_type as detect


# ── New-data-query path (require_viz_cue=True): data words must NOT force a type


def test_lines_data_word_does_not_force_line_chart():
    # The reported bug: "lines" must not be read as a "line" chart request.
    assert detect("Show the number of lines for each revenue bucket", require_viz_cue=True) is None


def test_table_data_reference_does_not_force_grid():
    assert (
        detect("I want to create a report from prepaid recharge table", require_viz_cue=True)
        is None
    )


def test_explicit_chart_requests_still_detected_on_new_query():
    assert detect("give me a pie chart", require_viz_cue=True) == "pie"
    assert detect("make it a bar chart", require_viz_cue=True) == "bar"
    assert detect("show revenue as a line graph", require_viz_cue=True) == "line"
    assert detect("show this as a data grid", require_viz_cue=True) == "table"


# ── Chart-type-only follow-up path (permissive default): "make it a pie"


def test_followup_change_type_is_permissive():
    assert detect("make it a pie") == "pie"
    assert detect("as line") == "line"
    assert detect("switch to table") == "table"


def test_whole_word_matching_avoids_false_positives():
    # Plurals / embedded words must not match the bare type token.
    assert detect("bars and lines") is None
    assert detect("areas of interest") is None
