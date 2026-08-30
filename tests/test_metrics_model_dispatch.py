import unittest
from unittest.mock import MagicMock, patch

from compass_model.base_metrics_model import BaseMetricsModel as BaseMetricsModelV1
from compass_model.base_metrics_model_v2 import BaseMetricsModel as BaseMetricsModelV2


def make_model(model_cls, first_metric):
    kwargs = dict(
        repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
        issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
        contributors_index="contributor-idx", release_index="release-idx", out_index="out-idx",
        from_date="2026-01-01", end_date="2026-08-01", level="repo", community="demo", source="github",
        json_file="repos.json", model_name="Demo Model",
        metrics_weights_thresholds={first_metric: {"weight": 1, "threshold": 1}},
    )
    if model_cls is BaseMetricsModelV2:
        kwargs["custom_fields"] = {"period": "month"}
    return model_cls(**kwargs)


class RepoLevelDispatchTest(unittest.TestCase):
    """repo 级别的分发应互斥：一个模型只应走一条 enrich 管线。
    修复前 if/if/else 级联导致命中 license/security（或 _year）分支的模型
    额外再跑一遍周期 enrich 管线。"""

    def test_security_metric_only_runs_version_pipeline_v2(self):
        model = make_model(BaseMetricsModelV2, "security_binary_artifact")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model_v2.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_version.assert_called_once()
        model.metrics_model_enrich_year.assert_not_called()
        model.metrics_model_enrich.assert_not_called()

    def test_period_metric_only_runs_period_pipeline_v2(self):
        model = make_model(BaseMetricsModelV2, "comment_frequency")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model_v2.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich.assert_called_once()
        model.metrics_model_enrich_year.assert_not_called()
        model.metrics_model_enrich_version.assert_not_called()

    def test_year_metric_only_runs_year_pipeline_v2(self):
        model = make_model(BaseMetricsModelV2, "issue_count_year")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model_v2.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_year.assert_called_once()
        model.metrics_model_enrich_version.assert_not_called()
        model.metrics_model_enrich.assert_not_called()

    def test_security_metric_only_runs_version_pipeline_v1(self):
        model = make_model(BaseMetricsModelV1, "security_vul_stat")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_version.assert_called_once()
        model.metrics_model_enrich_year.assert_not_called()
        model.metrics_model_enrich.assert_not_called()

    def test_period_metric_only_runs_period_pipeline_v1(self):
        model = make_model(BaseMetricsModelV1, "comment_frequency")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich.assert_called_once()
        model.metrics_model_enrich_year.assert_not_called()
        model.metrics_model_enrich_version.assert_not_called()

    def test_year_metric_only_runs_year_pipeline_v1(self):
        model = make_model(BaseMetricsModelV1, "issue_count_year")
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model.get_repo_list", return_value=["org/repo"]):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_year.assert_called_once()
        model.metrics_model_enrich_version.assert_not_called()
        model.metrics_model_enrich.assert_not_called()


class CommunityLevelDispatchTest(unittest.TestCase):
    def test_year_metric_does_not_also_run_period_pipeline_v2(self):
        model = make_model(BaseMetricsModelV2, "issue_count_year")
        model.level = "community"
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model_v2.get_community_repo_list",
                      return_value=(["org/sa-repo"], ["org/gov-repo"])):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_year.assert_called_once()
        model.metrics_model_enrich_version.assert_not_called()
        model.metrics_model_enrich.assert_not_called()

    def test_period_metric_runs_period_pipeline_v2(self):
        model = make_model(BaseMetricsModelV2, "comment_frequency")
        model.level = "community"
        model.metrics_model_enrich_year = MagicMock()
        model.metrics_model_enrich_version = MagicMock()
        model.metrics_model_enrich = MagicMock()

        with patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()), \
                patch("compass_model.base_metrics_model_v2.get_community_repo_list",
                      return_value=(["org/sa-repo"], ["org/gov-repo"])):
            model.metrics_model_metrics("http://es:9200")

        model.metrics_model_enrich_year.assert_not_called()
        model.metrics_model_enrich_version.assert_not_called()
        # software-artifact 与 governance 两个仓库集合各跑一次
        self.assertEqual(model.metrics_model_enrich.call_count, 2)


if __name__ == "__main__":
    unittest.main()
