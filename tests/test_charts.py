"""Tests for deterministic performance chart generation and embedding."""

from datetime import date, timedelta

import pandas as pd

from financial_researcher.services.briefing_email import (
    _build_chart_attachments,
    _inline_chart_images,
)
from financial_researcher.services.chart_generator import (
    ChartArtifact,
    build_charts_markdown,
    build_indexed_chart,
    generate_briefing_charts,
)
from financial_researcher.services.market_data import extract_history_series


def _history(days: int, start: float, drift: float) -> dict:
    today = date.today()
    dates = [(today - timedelta(days=days - i)).isoformat() for i in range(days)]
    closes = [round(start * (1 + drift) ** i, 4) for i in range(days)]
    return {"dates": dates, "closes": closes}


def _instrument(ticker: str, *, days: int = 300, start: float = 100.0, drift: float = 0.001) -> dict:
    return {
        "ticker": ticker,
        "name": f"{ticker} Fund",
        "history": _history(days, start, drift),
    }


class TestExtractHistorySeries:
    def test_returns_dates_and_closes(self):
        history = pd.DataFrame(
            {"Close": [10.0, 11.0, 12.0, 13.0]},
            index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-06", "2026-01-07"]),
        )
        series = extract_history_series(history)
        assert series is not None
        assert series["dates"][0] == "2026-01-02"
        assert series["closes"] == [10.0, 11.0, 12.0, 13.0]

    def test_returns_none_for_short_history(self):
        history = pd.DataFrame({"Close": [10.0, 11.0]})
        assert extract_history_series(history) is None


class TestBuildIndexedChart:
    def test_renders_png(self, tmp_path):
        out = tmp_path / "chart_1y.png"
        artifact = build_indexed_chart(
            [_instrument("AAA.MI"), _instrument("BBB.MI", drift=-0.0005)],
            horizon="1y",
            output_path=out,
            language="Italian",
            title="Andamento su 12 mesi — base 100",
        )
        assert artifact is not None
        assert out.is_file()
        assert out.stat().st_size > 0
        assert artifact.content_id.startswith("chart-1y-")

    def test_returns_none_without_history(self, tmp_path):
        artifact = build_indexed_chart(
            [{"ticker": "NO.MI", "name": "No data"}],
            horizon="1w",
            output_path=tmp_path / "x.png",
            language="English",
            title="Weekly",
        )
        assert artifact is None


class TestGenerateBriefingCharts:
    def test_generates_weekly_and_yearly(self, tmp_path):
        artifacts = generate_briefing_charts(
            [_instrument("AAA.MI"), _instrument("BBB.MI")],
            session="close",
            language="English",
            slug="watchlist_2026-06-13_close",
            out_dir=tmp_path,
        )
        horizons = {a.horizon for a in artifacts}
        assert horizons == {"1w", "1y"}
        for artifact in artifacts:
            assert artifact.path.is_file()


class TestBuildChartsMarkdown:
    def test_relative_paths_and_heading(self, tmp_path):
        briefings = tmp_path
        charts = tmp_path / "charts"
        charts.mkdir()
        artifact = ChartArtifact(
            horizon="1y",
            caption="12-month trend — indexed to 100",
            path=charts / "watchlist_close_1y.png",
            content_id="chart-1y-watchlist_close_1y",
        )
        md = build_charts_markdown([artifact], language="English", base_dir=briefings)
        assert "### Performance Charts" in md
        assert "![12-month trend — indexed to 100](charts/watchlist_close_1y.png)" in md

    def test_empty_when_no_artifacts(self):
        assert build_charts_markdown([], language="Italian") == ""


class TestEmailChartEmbedding:
    def test_attachment_and_cid_rewrite(self, tmp_path):
        png = tmp_path / "watchlist_close_1y.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n fake")
        artifact = ChartArtifact(
            horizon="1y",
            caption="cap",
            path=png,
            content_id="chart-1y-watchlist_close_1y",
        )
        attachments, src_to_cid = _build_chart_attachments([artifact])
        assert attachments[0]["content_id"] == "chart-1y-watchlist_close_1y"
        assert attachments[0]["content_type"] == "image/png"
        assert src_to_cid == {"charts/watchlist_close_1y.png": "chart-1y-watchlist_close_1y"}

        html = '<img alt="cap" src="charts/watchlist_close_1y.png">'
        rewritten = _inline_chart_images(html, src_to_cid)
        assert 'src="cid:chart-1y-watchlist_close_1y"' in rewritten
