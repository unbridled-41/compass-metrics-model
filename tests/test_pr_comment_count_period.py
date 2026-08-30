import unittest
from datetime import datetime
from unittest.mock import patch

from compass_metrics_v2.pr_metrics_v2 import get_period_range, pr_comment_count_by_period
from compass_model.base_metrics_model_v2 import BaseMetricsModel


SEARCH_RESPONSE = {
    "hits": {"total": {"value": 5}},
    "aggregations": {"count_of_uuid": {"value": 7}},
}


class RecordingClient:
    def __init__(self):
        self.search_calls = []

    def search(self, index=None, body=None):
        self.search_calls.append({"index": index, "body": body})
        return SEARCH_RESPONSE


class GetPeriodRangeTest(unittest.TestCase):
    """pr_metrics_v2 的 get_period_range 应与 issue/repo/developer/contributor/git
    各模块一致，将窗口结束时间规范化到周期最后一天。
    否则 enrich 循环传入周期第一天时，查询区间为 gte X lt X 的空区间，
    当前窗口的 PR 周期指标恒为 0。"""

    def test_month_window_covers_whole_month(self):
        start, end = get_period_range(datetime(2026, 8, 1), "month")
        self.assertEqual(start, datetime(2026, 8, 1))
        self.assertEqual(end, datetime(2026, 8, 31, 23, 59, 59))

    def test_quarter_window_covers_whole_quarter(self):
        start, end = get_period_range(datetime(2026, 8, 1), "quarter")
        self.assertEqual(start, datetime(2026, 7, 1))
        self.assertEqual(end, datetime(2026, 9, 30, 23, 59, 59))

    def test_year_window_covers_whole_year(self):
        start, end = get_period_range(datetime(2026, 2, 1), "year")
        self.assertEqual(start, datetime(2026, 1, 1))
        self.assertEqual(end, datetime(2026, 12, 31, 23, 59, 59))

    def test_invalid_period_rejected(self):
        with self.assertRaises(ValueError):
            get_period_range(datetime(2026, 8, 1), "week")


class PrCommentCountByPeriodTest(unittest.TestCase):
    def test_query_covers_current_period_not_a_single_moment(self):
        client = RecordingClient()
        result = pr_comment_count_by_period(client, "pr-idx", datetime(2026, 8, 1), ["org/repo"], "month")

        date_range = client.search_calls[0]["body"]["query"]["bool"]["filter"][0]["range"]["grimoire_creation_date"]
        self.assertEqual(date_range["gte"], "2026-08-01")
        self.assertEqual(date_range["lt"], "2026-08-31")
        self.assertEqual(result["pr_comment_count"], 7)

    def test_queries_pr_index_with_pr_filter(self):
        client = RecordingClient()
        pr_comment_count_by_period(client, "pr-idx", datetime(2026, 8, 1), ["org/repo"], "month")

        self.assertEqual(client.search_calls[0]["index"], "pr-idx")
        self.assertEqual(
            client.search_calls[0]["body"]["query"]["bool"]["must"][-1],
            {"match_phrase": {"pull_request": "true"}},
        )


class PrCommentCountSwitchBindingTest(unittest.TestCase):
    """metrics_switch 中 pr_comment_count_by_period 应绑定 PR 索引，
    而不是 issue 索引（其余 pr_* 指标均绑定 pr_index）。"""

    def test_pr_comment_count_queries_pr_index(self):
        client = RecordingClient()
        model = BaseMetricsModel(
            repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
            issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
            contributors_index="contributor-idx", release_index="release-idx", out_index="out-idx",
            from_date="2026-01-01", end_date="2026-08-01", level="repo", community="demo", source="github",
            json_file="repos.json", model_name="Demo Model",
            metrics_weights_thresholds={"pr_comment_count_by_period": {"weight": 1, "threshold": 1}},
            custom_fields={"period": "month"},
        )
        model.client = client

        model.get_metrics(datetime(2026, 8, 1), ["org/repo"], "month")

        self.assertEqual(client.search_calls[0]["index"], "pr-idx")


if __name__ == "__main__":
    unittest.main()
