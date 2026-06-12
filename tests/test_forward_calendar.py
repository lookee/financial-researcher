"""Tests for forward calendar prefetch."""

from datetime import date, datetime, timezone

from financial_researcher.services.forward_calendar import (
    _events_from_ticker_info,
    build_forward_calendar_table,
    build_recent_dated_events_table,
)


class TestForwardCalendarEvents:
    def test_extracts_earnings_in_window(self):
        item = {"ticker": "ISP.MI", "name": "Intesa", "type": "stock"}
        ts = int(datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc).timestamp())
        info = {"earningsDate": ts}
        events = _events_from_ticker_info(
            item,
            info,
            window_start=date(2026, 6, 12),
            window_end=date(2026, 6, 28),
        )
        assert len(events) == 1
        assert events[0]["date"] == "2026-06-20"
        assert events[0]["impact"] == "Earnings"

    def test_build_forward_table(self):
        table = build_forward_calendar_table(
            [
                {
                    "date": "2026-06-20",
                    "event": "Test earnings",
                    "tickers": "ISP.MI",
                    "impact": "Earnings",
                    "source_url": "https://example.com",
                }
            ]
        )
        assert "2026-06-20" in table
        assert "Earnings" in table


class TestRecentDatedEvents:
    def test_lists_past_headlines_only(self):
        table = build_recent_dated_events_table(
            [{"ticker": "SMH.MI", "name": "SMH"}],
            {
                "SMH.MI": [
                    {
                        "published_date": "2026-06-10",
                        "title": "Chip rally",
                        "url": "https://example.com/a",
                    }
                ]
            },
            as_of=date(2026, 6, 12),
        )
        assert "2026-06-10" in table
        assert "Chip rally" in table
