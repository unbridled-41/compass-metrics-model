import unittest

from compass_common.datetime import get_date_list_by_period


class GetDateListByPeriodTest(unittest.TestCase):
    """get_date_list_by_period 的文档说明支持 'day' / 'week' / 'month' / 'year'，
    且未知 period 应回退为每周（W-MON）。修复前 'day'/'week' 及未知值都会
    静默按月（'MS'）生成，导致周期粒度错误。"""

    def test_week_returns_mondays(self):
        dates = get_date_list_by_period("2026-08-03", "2026-08-24", "week")
        self.assertEqual(len(dates), 4)
        for date in dates:
            self.assertEqual(date.weekday(), 0)

    def test_day_returns_daily_dates(self):
        dates = get_date_list_by_period("2026-08-01", "2026-08-05", "day")
        self.assertEqual(len(dates), 5)

    def test_unknown_period_falls_back_to_weekly(self):
        dates = get_date_list_by_period("2026-08-03", "2026-08-24", "fortnight")
        self.assertEqual(len(dates), 4)

    def test_month_still_returns_month_starts(self):
        dates = get_date_list_by_period("2026-08-01", "2026-09-15", "month")
        self.assertEqual([date.strftime("%Y-%m-%d") for date in dates], ["2026-08-01", "2026-09-01"])

    def test_year_still_returns_year_starts(self):
        dates = get_date_list_by_period("2025-01-01", "2026-03-01", "year")
        self.assertEqual([date.strftime("%Y-%m-%d") for date in dates], ["2025-01-01", "2026-01-01"])


if __name__ == "__main__":
    unittest.main()
