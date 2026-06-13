"""Tests for Milan session inference from the wall clock."""

from datetime import date, datetime

from financial_researcher.services.watchlist_context import (
    MILAN_TZ,
    infer_milan_session,
    is_milan_market_closed,
    milan_market_holidays,
)


def _milan(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=MILAN_TZ)


class TestInferMilanSession:
    def test_weekday_pre_open_before_open(self):
        assert infer_milan_session(_milan(2026, 6, 12, 8, 50)) == "pre_open"

    def test_weekday_post_open_midmorning(self):
        assert infer_milan_session(_milan(2026, 6, 12, 9, 45)) == "post_open"

    def test_weekday_midday(self):
        assert infer_milan_session(_milan(2026, 6, 12, 13, 30)) == "midday"

    def test_weekday_close_evening(self):
        assert infer_milan_session(_milan(2026, 6, 12, 18, 0)) == "close"

    def test_saturday_always_close(self):
        # 11:01 would be post_open on a weekday, but market is closed.
        assert infer_milan_session(_milan(2026, 6, 13, 11, 1)) == "close"

    def test_sunday_always_close(self):
        assert infer_milan_session(_milan(2026, 6, 14, 8, 30)) == "close"

    def test_christmas_holiday_always_close(self):
        # 2026-12-25 is a Friday; intraday clock would say post_open at 10:00.
        assert infer_milan_session(_milan(2026, 12, 25, 10, 0)) == "close"

    def test_labour_day_holiday_always_close(self):
        # 2026-05-01 is a Friday.
        assert infer_milan_session(_milan(2026, 5, 1, 11, 0)) == "close"

    def test_easter_monday_holiday_always_close(self):
        # Easter 2026 is 2026-04-05; Easter Monday 2026-04-06.
        assert infer_milan_session(_milan(2026, 4, 6, 11, 0)) == "close"


class TestMilanMarketHolidays:
    def test_easter_derived_holidays_2026(self):
        holidays = milan_market_holidays(2026)
        assert date(2026, 4, 3) in holidays   # Good Friday
        assert date(2026, 4, 6) in holidays   # Easter Monday

    def test_fixed_holidays_present(self):
        holidays = milan_market_holidays(2026)
        assert date(2026, 1, 1) in holidays
        assert date(2026, 5, 1) in holidays
        assert date(2026, 12, 25) in holidays
        assert date(2026, 12, 26) in holidays

    def test_ferragosto_not_a_market_holiday(self):
        # Italian civic holiday but the exchange stays open.
        assert date(2026, 8, 15) not in milan_market_holidays(2026)

    def test_is_closed_on_holiday_and_weekend(self):
        assert is_milan_market_closed(_milan(2026, 12, 25, 10, 0)) is True
        assert is_milan_market_closed(_milan(2026, 6, 13, 10, 0)) is True

    def test_is_open_on_regular_weekday(self):
        assert is_milan_market_closed(_milan(2026, 6, 12, 10, 0)) is False
