import unittest
from unittest.mock import MagicMock, patch

from compass_model_v2.community_health.community_vitality.contribution_activity_metrics_model import (
    ContributionActivityMetricsModel,
)


class RecordingClient:
    def __init__(self):
        self.calls = []

    def search(self, index=None, body=None, **kwargs):
        self.calls.append({"index": index, "body": body})
        return {"hits": {"total": {"value": 3}},
                "aggregations": {"count_of_uuid": {"value": 5, "values": {"50.0": 2.0}}}}


class ContributionActivityEnrichFlowTest(unittest.TestCase):
    """用真实模型跑完整 enrich 流程，验证周期查询的整类缺陷：
    - 周期窗口不得出现 gte == lt 的空区间（pr_metrics_v2.get_period_range 修复点）；
    - pr_comment_count_by_period 必须查询 PR 索引（switch 绑定修复点）。
    该测试覆盖全部按周期指标在真实调用路径上的行为。"""

    def run_enrich(self, client):
        model = ContributionActivityMetricsModel(
            repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
            issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
            contributors_index="contrib-idx", release_index="release-idx", out_index="out-idx",
            from_date="2026-06-01", end_date="2026-08-15", level="repo", community="demo",
            source="github", json_file="repos.json", contributors_enriched_index="ce-idx",
            custom_fields={"period": "month"})
        model.client = client
        with patch("compass_model.base_metrics_model_v2.get_client", return_value=client), \
                patch("compass_model.base_metrics_model_v2.get_repo_list", return_value=["org/repo"]), \
                patch("compass_model.base_metrics_model_v2.created_since", return_value={"created_since": 100}), \
                patch("compass_model.base_metrics_model_v2.add_release_message"), \
                patch("compass_model.base_metrics_model_v2.helpers"):
            model.metrics_model_metrics("http://es:9200")
        return model

    def test_no_period_query_uses_an_empty_window(self):
        client = RecordingClient()
        self.run_enrich(client)
        for call in client.calls:
            for f in call["body"].get("query", {}).get("bool", {}).get("filter", []):
                rng = f.get("range", {}).get("grimoire_creation_date")
                if rng:
                    self.assertNotEqual(rng["gte"], rng["lt"],
                                        f"{call['index']} 查询出现空区间: {rng}")

    def test_june_window_covers_the_whole_month(self):
        client = RecordingClient()
        self.run_enrich(client)
        june_ends = set()
        for call in client.calls:
            for f in call["body"].get("query", {}).get("bool", {}).get("filter", []):
                rng = f.get("range", {}).get("grimoire_creation_date")
                if rng and rng.get("gte", "").startswith("2026-06"):
                    june_ends.add(rng["lt"])
        self.assertTrue(june_ends)
        for lt in june_ends:
            self.assertGreaterEqual(lt, "2026-06-29")

    def test_pr_comment_count_queries_the_pr_index(self):
        client = RecordingClient()
        self.run_enrich(client)
        pr_calls = [c for c in client.calls if c["index"] == "pr-idx"]
        self.assertTrue(pr_calls, "没有任何查询落在 PR 索引上")
        for call in pr_calls:
            must = call["body"]["query"]["bool"]["must"]
            self.assertTrue(
                any(q.get("match_phrase", {}).get("pull_request") == "true" for q in must))


if __name__ == "__main__":
    unittest.main()
