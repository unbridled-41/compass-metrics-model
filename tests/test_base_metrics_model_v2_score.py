import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from compass_model.base_metrics_model_v2 import BaseMetricsModel


def make_model():
    return BaseMetricsModel(
        repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
        issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
        contributors_index="contributor-idx", release_index="release-idx", out_index="out-idx",
        from_date="2026-01-01", end_date="2026-08-01", level="repo", community="demo", source="github",
        json_file="repos.json", model_name="Demo Model",
        metrics_weights_thresholds={"comment_frequency": {"weight": 1, "threshold": 15}},
        custom_fields={"period": "month"},
    )


def enrich_patches():
    return [
        patch("compass_model.base_metrics_model_v2.get_client", return_value=MagicMock()),
        patch("compass_model.base_metrics_model_v2.add_release_message"),
        patch("compass_model.base_metrics_model_v2.created_since", return_value={"created_since": 100}),
        patch("compass_model.base_metrics_model_v2.get_date_list_by_period",
              return_value=[datetime(2026, 8, 1)]),
    ]


class MetricsModelEnrichScoreTest(unittest.TestCase):
    """metrics_model_enrich 中评分只应计算一次，且评分异常时应回退为 0 而不是中断整个任务。"""

    def test_score_failure_falls_back_to_zero_instead_of_crashing(self):
        model = make_model()
        patches = enrich_patches()
        with patches[0], patches[1], patches[2], patches[3], \
                patch("compass_model.base_metrics_model_v2.helpers") as helpers_mock:
            model.get_metrics = MagicMock(return_value=({"comment_frequency": 3}, {}))
            model.metrics_decay = MagicMock(side_effect=lambda metrics_data, last_data: metrics_data)
            model.get_metrics_score = MagicMock(side_effect=RuntimeError("boom"))

            model.metrics_model_enrich(["org/repo"], "org/repo", "repo")

            bulk_actions = []
            for call in helpers_mock.return_value.bulk.call_args_list:
                bulk_actions.extend(call.kwargs["actions"])
            self.assertEqual(len(bulk_actions), 1)
            self.assertEqual(bulk_actions[0]["_source"]["score"], 0)

    def test_score_is_computed_exactly_once_per_period(self):
        model = make_model()
        patches = enrich_patches()
        with patches[0], patches[1], patches[2], patches[3], \
                patch("compass_model.base_metrics_model_v2.helpers"):
            model.get_metrics = MagicMock(return_value=({"comment_frequency": 3}, {}))
            model.metrics_decay = MagicMock(side_effect=lambda metrics_data, last_data: metrics_data)
            model.get_metrics_score = MagicMock(return_value=0.42)

            model.metrics_model_enrich(["org/repo"], "org/repo", "repo")

            self.assertEqual(model.get_metrics_score.call_count, 1)


if __name__ == "__main__":
    unittest.main()
