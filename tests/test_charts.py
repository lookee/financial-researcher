"""Tests for deterministic performance chart generation and embedding."""

from datetime import date, datetime, timedelta

import pandas as pd

from financial_researcher.services.briefing_email import (
    _build_chart_attachments,
    _inline_chart_images,
)
from financial_researcher.services.chart_generator import (
    ChartArtifact,
    build_charts_markdown,
    build_indexed_chart,
    build_performance_heatmap,
    build_risk_return_scatter,
    build_watchlist_breadth_chart,
    generate_briefing_charts,
    resolve_breadth_metrics,
    resolve_chart_horizons,
    resolve_heatmap_columns,
)
from financial_researcher.services.market_data import (
    extract_history_series,
    extract_intraday_series,
)


def _history(days: int, start: float, drift: float) -> dict:
    today = date.today()
    dates = [(today - timedelta(days=days - i)).isoformat() for i in range(days)]
    closes = [round(start * (1 + drift) ** i, 4) for i in range(days)]
    return {"dates": dates, "closes": closes}


def _intraday(bars: int, start: float, drift: float) -> dict:
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    timestamps = [
        (base + timedelta(minutes=5 * i)).isoformat(timespec="minutes")
        for i in range(bars)
    ]
    closes = [round(start * (1 + drift) ** i, 4) for i in range(bars)]
    return {"timestamps": timestamps, "closes": closes}


def _instrument(
    ticker: str,
    *,
    days: int = 300,
    start: float = 100.0,
    drift: float = 0.001,
    intraday_bars: int = 0,
    performance: dict | None = None,
    volatility_30d: float | None = 15.0,
) -> dict:
    entry = {
        "ticker": ticker,
        "name": f"{ticker} Fund",
        "type": "etf",
        "history": _history(days, start, drift),
        "performance": performance
        or {"1d": 1.2, "1w": -0.5, "1m": 3.0, "ytd": 10.0, "1y": 15.0},
    }
    if volatility_30d is not None:
        entry["volatility_30d"] = volatility_30d
    if intraday_bars:
        entry["intraday"] = _intraday(intraday_bars, start, drift)
    return entry


class TestResolveHeatmapColumns:
    def test_pre_open_excludes_1d(self):
        assert resolve_heatmap_columns("pre_open") == ("1w", "1m", "ytd")

    def test_close_includes_1d(self):
        assert resolve_heatmap_columns("close") == ("1d", "1w", "1m", "ytd")


class TestResolveBreadthMetrics:
    def test_pre_open_week_only(self):
        assert resolve_breadth_metrics("pre_open") == ("1w",)

    def test_close_day_and_week(self):
        assert resolve_breadth_metrics("close") == ("1d", "1w")


class TestResolveChartHorizons:
    def test_pre_open_week_only(self):
        assert resolve_chart_horizons("pre_open") == ("1w",)

    def test_midday_intraday_and_week(self):
        assert resolve_chart_horizons("midday") == ("1d", "1w")

    def test_close_full_set(self):
        assert resolve_chart_horizons("close") == ("1d", "1w", "1m", "1y")


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


class TestExtractIntradaySeries:
    def test_returns_timestamps_and_closes(self):
        index = pd.to_datetime(
            ["2026-06-13 09:05:00", "2026-06-13 09:10:00", "2026-06-13 09:15:00"]
        )
        intraday = pd.DataFrame({"Close": [100.0, 100.5, 101.0]}, index=index)
        series = extract_intraday_series(intraday)
        assert series is not None
        assert len(series["timestamps"]) == 3
        assert series["closes"] == [100.0, 100.5, 101.0]


class TestBuildIndexedChart:
    def test_renders_yearly_png(self, tmp_path):
        out = tmp_path / "chart_1y.png"
        artifact = build_indexed_chart(
            [_instrument("AAA.MI"), _instrument("BBB.MI", drift=-0.0005)],
            horizon="1y",
            session="close",
            output_path=out,
            language="Italian",
            title="Andamento su 12 mesi — base 100",
        )
        assert artifact is not None
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_renders_intraday_png(self, tmp_path):
        out = tmp_path / "chart_1d.png"
        artifact = build_indexed_chart(
            [_instrument("AAA.MI", intraday_bars=20)],
            horizon="1d",
            session="midday",
            output_path=out,
            language="English",
            title="Intraday trend (partial) — indexed to 100",
        )
        assert artifact is not None
        assert "partial" in artifact.caption.lower()
        assert out.is_file()

    def test_returns_none_without_history(self, tmp_path):
        artifact = build_indexed_chart(
            [{"ticker": "NO.MI", "name": "No data"}],
            horizon="1w",
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
            title="Weekly",
        )
        assert artifact is None


class TestBuildPerformanceHeatmap:
    def test_renders_heatmap_png(self, tmp_path):
        out = tmp_path / "heatmap.png"
        artifact = build_performance_heatmap(
            [
                _instrument("AAA.MI", performance={"1d": 2.0, "1w": 1.0, "1m": 5.0, "ytd": 12.0}),
                _instrument("BBB.MI", performance={"1d": -1.5, "1w": 0.2, "1m": -2.0, "ytd": 3.0}),
            ],
            session="close",
            output_path=out,
            language="English",
        )
        assert artifact is not None
        assert artifact.horizon == "heatmap"
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_pre_open_three_columns(self, tmp_path):
        artifact = build_performance_heatmap(
            [_instrument("AAA.MI")],
            session="pre_open",
            output_path=tmp_path / "heatmap_pre.png",
            language="Italian",
        )
        assert artifact is not None
        assert "settimana" in artifact.caption.lower()

    def test_skips_benchmark_rows(self, tmp_path):
        artifact = build_performance_heatmap(
            [{"ticker": "FTSEMIB.MI", "type": "benchmark", "performance": {"1d": 0.5}}],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None


class TestBuildRiskReturnScatter:
    def test_renders_scatter_png(self, tmp_path):
        out = tmp_path / "risk_return.png"
        artifact = build_risk_return_scatter(
            [
                _instrument("AAA.MI", volatility_30d=12.0, performance={"ytd": 25.0}),
                _instrument("BBB.MI", volatility_30d=22.0, performance={"ytd": -5.0}),
            ],
            session="close",
            output_path=out,
            language="English",
        )
        assert artifact is not None
        assert artifact.horizon == "risk_return"
        assert "volatility" in artifact.caption.lower()
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_italian_caption(self, tmp_path):
        artifact = build_risk_return_scatter(
            [
                _instrument("AAA.MI", volatility_30d=10.0, performance={"ytd": 8.0}),
                _instrument("BBB.MI", volatility_30d=18.0, performance={"ytd": 2.0}),
            ],
            session="close",
            output_path=tmp_path / "scatter_it.png",
            language="Italian",
        )
        assert artifact is not None
        assert "volatilità" in artifact.caption.lower()

    def test_returns_none_with_single_point(self, tmp_path):
        artifact = build_risk_return_scatter(
            [_instrument("AAA.MI")],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None

    def test_returns_none_without_volatility(self, tmp_path):
        artifact = build_risk_return_scatter(
            [
                _instrument("AAA.MI", volatility_30d=None),
                _instrument("BBB.MI", volatility_30d=None),
            ],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None

    def test_skips_benchmark_rows(self, tmp_path):
        artifact = build_risk_return_scatter(
            [
                {
                    "ticker": "FTSEMIB.MI",
                    "type": "benchmark",
                    "volatility_30d": 10.0,
                    "performance": {"ytd": 5.0},
                },
                _instrument("AAA.MI"),
            ],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None


class TestBuildWatchlistBreadthChart:
    def test_renders_breadth_png(self, tmp_path):
        out = tmp_path / "breadth.png"
        artifact = build_watchlist_breadth_chart(
            [
                _instrument("AAA.MI", performance={"1d": 2.0, "1w": 1.0}),
                _instrument("BBB.MI", performance={"1d": -1.5, "1w": -0.2}),
                _instrument("CCC.MI", performance={"1d": 0.5, "1w": 0.0}),
            ],
            session="close",
            output_path=out,
            language="English",
        )
        assert artifact is not None
        assert artifact.horizon == "breadth"
        assert "breadth" in artifact.caption.lower()
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_pre_open_week_only(self, tmp_path):
        artifact = build_watchlist_breadth_chart(
            [
                _instrument("AAA.MI", performance={"1w": 1.0}),
                _instrument("BBB.MI", performance={"1w": -0.5}),
            ],
            session="pre_open",
            output_path=tmp_path / "breadth_pre.png",
            language="Italian",
        )
        assert artifact is not None
        assert "settimana" in artifact.caption.lower()

    def test_close_renders_two_horizons(self, tmp_path):
        artifact = build_watchlist_breadth_chart(
            [
                _instrument("AAA.MI", performance={"1d": 1.0, "1w": 2.0}),
                _instrument("BBB.MI", performance={"1d": -0.5, "1w": -1.0}),
                _instrument("CCC.MI", performance={"1d": 0.2, "1w": 0.0}),
            ],
            session="close",
            output_path=tmp_path / "breadth_close.png",
            language="English",
        )
        assert artifact is not None
        assert "day and week" in artifact.caption.lower()

    def test_returns_none_with_single_instrument(self, tmp_path):
        artifact = build_watchlist_breadth_chart(
            [_instrument("AAA.MI")],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None

    def test_skips_benchmark_rows(self, tmp_path):
        artifact = build_watchlist_breadth_chart(
            [
                {
                    "ticker": "FTSEMIB.MI",
                    "type": "benchmark",
                    "performance": {"1d": 0.5, "1w": 0.2},
                },
                _instrument("AAA.MI"),
            ],
            session="close",
            output_path=tmp_path / "x.png",
            language="English",
        )
        assert artifact is None


class TestGenerateBriefingCharts:
    def test_close_generates_heatmap_and_line_charts(self, tmp_path):
        instruments = [
            _instrument("AAA.MI", intraday_bars=20),
            _instrument("BBB.MI", intraday_bars=20),
        ]
        artifacts = generate_briefing_charts(
            instruments,
            session="close",
            language="English",
            slug="watchlist_2026-06-13_close",
            out_dir=tmp_path,
        )
        horizons = {a.horizon for a in artifacts}
        assert horizons == {"heatmap", "risk_return", "breadth", "1d", "1w", "1m", "1y"}
        assert artifacts[0].horizon == "heatmap"
        assert artifacts[1].horizon == "risk_return"
        assert artifacts[2].horizon == "breadth"

    def test_midday_generates_heatmap_intraday_and_week(self, tmp_path):
        instruments = [
            _instrument("AAA.MI", intraday_bars=15),
            _instrument("BBB.MI", intraday_bars=15),
        ]
        artifacts = generate_briefing_charts(
            instruments,
            session="midday",
            language="Italian",
            slug="watchlist_2026-06-13_midday",
            out_dir=tmp_path,
        )
        assert {a.horizon for a in artifacts} == {
            "heatmap",
            "risk_return",
            "breadth",
            "1d",
            "1w",
        }

    def test_pre_open_heatmap_and_week_line(self, tmp_path):
        artifacts = generate_briefing_charts(
            [_instrument("AAA.MI"), _instrument("BBB.MI")],
            session="pre_open",
            language="English",
            slug="watchlist_2026-06-13_pre_open",
            out_dir=tmp_path,
        )
        assert {a.horizon for a in artifacts} == {"heatmap", "risk_return", "breadth", "1w"}

    def test_single_instrument_skips_scatter_and_breadth(self, tmp_path):
        artifacts = generate_briefing_charts(
            [_instrument("AAA.MI", intraday_bars=15)],
            session="midday",
            language="English",
            slug="watchlist_single",
            out_dir=tmp_path,
        )
        horizons = {a.horizon for a in artifacts}
        assert "risk_return" not in horizons
        assert "breadth" not in horizons


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
