import unittest

from compass_model.base_metrics_model import BaseMetricsModel as BaseMetricsModelV1
from compass_model.base_metrics_model_v2 import BaseMetricsModel as BaseMetricsModelV2


def base_kwargs():
    return dict(
        repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
        issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
        contributors_index="contributor-idx", release_index="release-idx", out_index="out-idx",
        from_date="2026-01-01", end_date="2026-08-01", level="repo", community="demo", source="github",
        json_file="repos.json", model_name="Demo Model",
    )


class FailFastMetricValidationTest(unittest.TestCase):
    """未知的 metric 名称应在模型构造时立即报错并点名具体指标，
    而不是等 add_release_message / 周期富集开始后才抛出笼统的
    "Invalid metric"，导致一次运行在消耗大量计算后失败。"""

    def test_unknown_metric_fails_at_construction_v2(self):
        with self.assertRaises(Exception) as ctx:
            BaseMetricsModelV2(
                metrics_weights_thresholds={"totally_unknown_metric": {"weight": 1, "threshold": 1}},
                custom_fields={"period": "month"}, **base_kwargs())
        self.assertIn("totally_unknown_metric", str(ctx.exception))

    def test_unknown_metric_fails_at_construction_v1(self):
        with self.assertRaises(Exception) as ctx:
            BaseMetricsModelV1(
                metrics_weights_thresholds={"totally_unknown_metric": {"weight": 1, "threshold": 1}},
                **base_kwargs())
        self.assertIn("totally_unknown_metric", str(ctx.exception))

    def test_missing_default_threshold_names_metric_and_level_v2(self):
        # binary_artifacts 是合法指标，但 thresholds.yaml 中没有它的默认阈值，
        # threshold 传 None 时应给出明确报错而不是裸 KeyError
        with self.assertRaises(Exception) as ctx:
            BaseMetricsModelV2(
                metrics_weights_thresholds={"binary_artifacts": {"weight": 1, "threshold": None}},
                custom_fields={"period": "month"}, **base_kwargs())
        message = str(ctx.exception)
        self.assertIn("binary_artifacts", message)
        self.assertIn("repo", message)

    def test_valid_metric_config_still_constructs(self):
        model = BaseMetricsModelV2(
            metrics_weights_thresholds={"comment_frequency": {"weight": 1, "threshold": 15}},
            custom_fields={"period": "month"}, **base_kwargs())
        self.assertEqual(model.metrics_weights_thresholds["comment_frequency"]["threshold"], 15)


if __name__ == "__main__":
    unittest.main()
