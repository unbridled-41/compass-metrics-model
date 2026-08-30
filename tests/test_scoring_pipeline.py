import unittest

from compass_model.base_metrics_model import (
    BaseMetricsModel as BaseMetricsModelV1,
    cache_last_metrics_data,
    decrease_decay,
    increment_decay,
)
from compass_common.algorithm_utils import (
    get_param_score,
    get_score_by_criticality_score,
    get_score_by_criticality_score_with_mapping,
)


def make_v1_model(metrics_weights_thresholds):
    return BaseMetricsModelV1(
        repo_index="repo-idx", git_index="git-idx", issue_index="issue-idx", pr_index="pr-idx",
        issue_comments_index="issue-cmt-idx", pr_comments_index="pr-cmt-idx",
        contributors_index="contributor-idx", release_index="release-idx", out_index="out-idx",
        from_date="2026-01-01", end_date="2026-08-01", level="repo", community="demo", source="github",
        json_file="repos.json", model_name="Demo Model",
        metrics_weights_thresholds=metrics_weights_thresholds)


class DecayFormulaTest(unittest.TestCase):
    """decay 系数 0.0027/天：时间越久，增量指标向 threshold 逼近、
    频次指标向 0 衰减，且分别被 threshold / 0 截断。"""

    def test_increment_decay_grows_toward_threshold(self):
        self.assertAlmostEqual(increment_decay(10, 15, 30), 11.215)
        self.assertEqual(increment_decay(10, 15, 10 ** 6), 15)  # 上界为 threshold

    def test_decrease_decay_falls_toward_zero(self):
        self.assertAlmostEqual(decrease_decay(10, 15, 30), 8.785)
        self.assertEqual(decrease_decay(1, 15, 10 ** 6), 0)  # 下界为 0


class CacheLastMetricsDataTest(unittest.TestCase):
    def test_only_decay_metrics_with_values_are_cached(self):
        last = {}
        cache_last_metrics_data({
            "comment_frequency": 5,
            "issue_first_reponse_avg": None,      # decay 名单内但值为 None -> 不缓存
            "code_review_count": 3,
            "not_a_decay_metric": 9,              # 不在名单内 -> 不缓存
            "grimoire_creation_date": "2026-08-01T00:00:00",
        }, last)
        self.assertEqual(last, {
            "comment_frequency": [5, "2026-08-01T00:00:00"],
            "code_review_count": [3, "2026-08-01T00:00:00"],
        })


class MetricsDecayTest(unittest.TestCase):
    def setUp(self):
        self.model = make_v1_model({"comment_frequency": {"weight": 1, "threshold": 15}})

    def test_missing_metric_decays_from_last_value(self):
        metrics_data = {"comment_frequency": None, "grimoire_creation_date": "2026-08-01T00:00:00"}
        last = {"comment_frequency": [10, "2026-07-01T00:00:00"]}
        # 10 - 0.0027 * 15 * 31 天 = 8.7445
        self.assertEqual(self.model.metrics_decay(metrics_data, last)["comment_frequency"], 8.7445)

    def test_present_metric_is_untouched(self):
        metrics_data = {"comment_frequency": 7, "grimoire_creation_date": "2026-08-01T00:00:00"}
        last = {"comment_frequency": [10, "2026-07-01T00:00:00"]}
        self.assertEqual(self.model.metrics_decay(metrics_data, last)["comment_frequency"], 7)

    def test_no_last_data_returns_input(self):
        metrics_data = {"comment_frequency": None, "grimoire_creation_date": "2026-08-01T00:00:00"}
        self.assertIs(self.model.metrics_decay(metrics_data, None), metrics_data)


class CriticalityScoreTest(unittest.TestCase):
    def test_param_at_threshold_scores_full_weight(self):
        self.assertAlmostEqual(get_score_by_criticality_score(
            {"m": 10}, {"m": {"weight": 1, "threshold": 10}}), 1.0)

    def test_param_below_threshold_is_log_ratio(self):
        # 返回值是 log-ratio 的加权平均：单指标时权重约掉，
        # log(1+5)/log(1+10) = 0.74722
        self.assertAlmostEqual(get_score_by_criticality_score(
            {"m": 5}, {"m": {"weight": 2, "threshold": 10}}), 0.74722, places=4)

    def test_none_param_treated_by_weight_sign(self):
        # 正向权重：None 视为 0（最差）
        self.assertAlmostEqual(get_score_by_criticality_score(
            {"m": None}, {"m": {"weight": 1, "threshold": 10}}), 0.0)
        # 负向权重：None 视为 threshold（最差，得负分）
        self.assertAlmostEqual(get_score_by_criticality_score(
            {"m": None}, {"m": {"weight": -1, "threshold": 10}}), 1.0)

    def test_zero_total_weight_returns_zero(self):
        self.assertEqual(get_score_by_criticality_score({}, {}), 0.0)

    def test_negative_metrics_weight_sign_flip_at_init(self):
        model = make_v1_model({"updated_since": {"weight": 2, "threshold": 120}})
        self.assertEqual(model.metrics_weights_thresholds["updated_since"]["weight"], -2)

    def test_v1_score_normalizes_to_one_at_threshold(self):
        model = make_v1_model({"comment_frequency": {"weight": 1, "threshold": 15}})
        self.assertAlmostEqual(model.get_metrics_score({"comment_frequency": 15}), 1.0)
        self.assertAlmostEqual(model.get_metrics_score({"comment_frequency": 0}), 0.0)


class CriticalityScoreMappingTest(unittest.TestCase):
    def test_repo_stars_maps_to_stars_added(self):
        score = get_score_by_criticality_score_with_mapping(
            {"stars_added": 50},
            {"repo_stars_by_period": {"weight": 2, "threshold": 100}})
        # log(51)/log(101) = 0.85194（加权平均，单指标权重约掉）
        self.assertAlmostEqual(score, 0.85194, places=4)

    def test_reverse_metric_scores_linearly_downward(self):
        config = {"security_binary_artifact": {"weight": 1, "threshold": 10, "is_reverse": True}}
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"security_binary_artifact": 0}, config), 1.0)
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"security_binary_artifact": 5}, config), 0.5)
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"security_binary_artifact": 20}, config), 0.0)

    def test_minus_one_means_unknown_half_credit(self):
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"x": -1}, {"x": {"weight": 1, "threshold": 10}}), 0.5)

    def test_none_metric_contributes_zero_but_dilutes_score(self):
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"x": None}, {"x": {"weight": 1, "threshold": 10}}), 0.0)

    def test_dict_param_is_averaged(self):
        score = get_score_by_criticality_score_with_mapping(
            {"pr_review_time_by_size": {"small": 2, "large": 4}},
            {"pr_review_time_by_size": {"weight": 1, "threshold": 10}})
        self.assertAlmostEqual(score, get_param_score(3, 10, 1), places=4)

    def test_non_positive_threshold_forced_to_one(self):
        self.assertAlmostEqual(get_score_by_criticality_score_with_mapping(
            {"x": 5}, {"x": {"weight": 1, "threshold": 0}}), 1.0)


if __name__ == "__main__":
    unittest.main()
